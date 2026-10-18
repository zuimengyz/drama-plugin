"""Target reference production, using existing still compile/review/media owners.

The existing Runtime advances these capabilities. Only references enter its
checkpoint; image requests, receipts and review originals remain in the Ledger.
No legacy Work production stage or second production loop is involved.
"""
from __future__ import annotations
from copy import deepcopy
from contextlib import AsyncExitStack
import asyncio
from pathlib import Path
from typing import Any, Literal, Self, TYPE_CHECKING
import httpx
from pydantic import Field, JsonValue, TypeAdapter, ValidationInfo, field_validator, model_validator
from drama_plugin.contracts.base import canonical_json, dump_contract, sha256_canonical
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.creative_engine.contracts import AuthorRequest
from drama_plugin.persistence.review import UserDecisionRecord
from drama_plugin.runtime.capabilities import TargetCapability
from drama_plugin.runtime.contracts import (ActionKind, ArtifactReference, CapabilityInput,
    CapabilityResult, DecisionCategory, RecoveryClass, ResultStatus, RuntimeAction,
    RuntimeContract, RuntimeRun, RuntimeScope, RuntimeState, RuntimeWorkflow, UserDecisionRequest)
from drama_plugin.visual.frame_request import FrameSpec, compile_frame, verify_compiled
from drama_plugin.visual import production as still
from drama_plugin.visual.ark_submission import retained_receipt, submit_reserved
from drama_plugin.media_delivery import MediaIdentity, persist_media, verify_media
from drama_plugin.contracts.media import MediaType
from drama_plugin.exceptions import ProviderError, MediaImportSourceError

if TYPE_CHECKING:
    from drama_plugin.plugin import DramaPlugin

WORKFLOW = 'specialized-asset-reference:v1'
OWNER = 'asset-reference-production'
INDEX = 'asset-reference-current'
PREFIX = 'specialized-assets.reference.'


class ReferenceProductionRecord(RuntimeContract):
    schema_version: Literal['asset-reference-production-v1'] = 'asset-reference-production-v1'
    run_id: str
    scope: RuntimeScope
    preparation_ref: SourcePin
    requirement_key: str
    author_context_ref: SourcePin
    frame: dict[str, Any] | None = None
    stage: dict[str, Any] | None = None
    receipt: dict[str, Any] | None = None
    delivery: dict[str, Any] | None = None
    quote: dict[str, Any] | None = None
    balance: dict[str, Any] | None = None
    execution_binding: dict[str, Any] | None = None
    budget: float | None = Field(default=None, gt=0)
    budget_unit: Literal['credits', 'CNY', 'USD'] = 'CNY'
    cost_ref: ArtifactReference | None = None
    adoption_ref: ArtifactReference | None = None
    asset_id: str | None = None
    required_action: str | None = None
    fingerprint: str = Field(pattern='^[a-f0-9]{64}$')

    @field_validator('frame', 'stage', 'receipt', 'delivery', 'quote', 'balance', 'execution_binding')
    @classmethod
    def json_evidence(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        # Existing still contracts use dictionary snapshots; admit JSON only,
        # then replay their unchanged compiler/campaign validation below.
        return TypeAdapter(dict[str, JsonValue]).validate_python(value) if value is not None else None

    @classmethod
    def seal(cls, **values: Any) -> Self:
        value = cls.model_validate({**values, 'fingerprint': '0'*64}, context='seal')
        return cls.model_validate({**dump_contract(value), 'fingerprint': sha256_canonical(
            value.model_dump(mode='json', by_alias=True, exclude={'fingerprint'}))})

    @model_validator(mode='after')
    def integrity(self, info: ValidationInfo) -> Self:
        if info.context != 'seal' and self.fingerprint != sha256_canonical(
                self.model_dump(mode='json', by_alias=True, exclude={'fingerprint'})):
            raise ValueError('REFERENCE_PRODUCTION_FINGERPRINT_MISMATCH')
        if self.frame is not None:
            verify_compiled(self.frame)
        if self.stage is not None:
            still.check_campaign(self.stage)
            if self.frame is None or list(self.stage['frames'].values()) != [self.frame]:
                raise ValueError('REFERENCE_STAGE_FRAME_MISMATCH')
        return self

    def artifact_reference(self) -> ArtifactReference:
        return ArtifactReference(owner=OWNER, artifact_ref=OWNER+':'+self.fingerprint, version=1)


def reference_workflow() -> RuntimeWorkflow:
    return RuntimeWorkflow(workflow_id=WORKFLOW, steps=tuple(RuntimeAction(
        kind=ActionKind.CALL_CAPABILITY, capability_key=PREFIX+k+':v1')
        for k in ('prepare', 'reserve', 'submit', 'persist', 'review', 'adopt', 'register')))


class TargetReferenceProduction:
    lifecycle = 'TARGET'

    def __init__(self, plugin: DramaPlugin):
        self.plugin = plugin
        assert plugin.ledger is not None and plugin.execution is not None
        self.ledger, self.sequence = plugin.ledger, plugin.asset_sequence
        self.cache = plugin.execution.media.directory / 'asset-references'
        self.lock = plugin.execution.store.lock

    def registrations(self) -> dict[str, TargetCapability]:
        return {PREFIX+k+':v1': TargetCapability(getattr(self, k), replay_safe=True)
            for k in ('prepare', 'reserve', 'submit', 'persist', 'review', 'adopt', 'register')}

    def get(self, run_id: str) -> ReferenceProductionRecord:
        ref = ArtifactReference.model_validate(self.ledger.get_index(INDEX, run_id))
        body, scope, fingerprint = self.ledger.get_artifact(OWNER, ref)
        value = ReferenceProductionRecord.model_validate(body)
        if (value.run_id != run_id or self.ledger.load_run(run_id).scope != value.scope
                or value.artifact_reference() != ref or value.scope != scope or value.fingerprint != fingerprint):
            raise ValueError('REFERENCE_PRODUCTION_IDENTITY_MISMATCH')
        return value

    def save(self, prior: ReferenceProductionRecord, **changes: Any) -> ReferenceProductionRecord:
        if changes and 'required_action' not in changes:
            changes['required_action'] = None
        value = ReferenceProductionRecord.seal(**{**prior.model_dump(exclude={'fingerprint'}), **changes})
        ref = value.artifact_reference()
        with self.ledger.transaction(write=True) as db:
            current = db.execute('SELECT value_json FROM ledger_index WHERE index_type=? AND index_key=?',
                (INDEX, value.run_id)).fetchone()
            if current and ArtifactReference.model_validate_json(current['value_json']) != prior.artifact_reference():
                raise ValueError('REFERENCE_CHECKPOINT_CHANGED')
            self.ledger._put_artifact(db, OWNER, ref, value.scope, value.fingerprint, value)
            db.execute('INSERT OR REPLACE INTO ledger_index VALUES (?,?,?,?,?,?)',
                (INDEX, value.run_id, value.scope.work_id, value.scope.scene_id, value.scope.shot_id, canonical_json(ref)))
        self.ledger.notify_retained(OWNER,ref,value.scope,value.fingerprint)
        return value

    def item(self, value: ReferenceProductionRecord) -> dict[str, Any]:
        packet = self.sequence.objects.read_ref(value.preparation_ref)
        selected = self.sequence.objects._path('asset-scene-design', [packet['narrativeRef']['fingerprint'], packet['sceneId']])
        if (packet.get('schemaVersion') != 'specialized-asset-preparation-v1'
                or (packet['workId'], packet['sceneId']) != (value.scope.work_id, value.scope.scene_id)
                or not selected.exists()
                or SourcePin.model_validate(self.sequence.objects._read(selected)) != value.preparation_ref):
            raise ValueError('REFERENCE_PREPARATION_AUTHORITY_MISMATCH')
        item = next(r for r in packet['requirements'] if r['requirementKey'] == value.requirement_key)
        if item.get('reuseAssetId'):
            raise ValueError('REFERENCE_REUSE_DOES_NOT_REQUIRE_GENERATION')
        original = self.sequence.objects.read_ref(SourcePin.model_validate(item['designRef']))
        if sha256_canonical(original) != value.requirement_key:
            raise ValueError('REFERENCE_DESIGN_CHANGED')
        return dict(item)

    async def artwork_item(self, value: ReferenceProductionRecord) -> dict[str, Any]:
        item = self.item(value)
        if item.get('inheritedFromAssetId'):
            parent = await self.sequence.assets.get_asset(item['inheritedFromAssetId'])
            basis = parent.content.get('specializedAsset', {})
            if (parent.work_id != value.scope.work_id or not self.sequence._proof(parent)
                    or basis.get('stableIdentity') != item['stableIdentity']
                    or basis.get('subjectId') != item['subjectId']):
                raise ValueError('INHERITED_ASSET_IDENTITY_RECOVERY')
            item = {**item, 'inheritedDesign': basis['design'], 'inheritedDesignRef': basis['designRef']}
        return item

    async def pending(self, preparation_ref: SourcePin, parent_run_id: str,
                      request: AuthorRequest, *, requirement_key: str | None = None) -> CapabilityResult:
        lock = self.sequence._locks.setdefault('prepare:' + request.scope.work_id, asyncio.Lock())
        async with lock:
            return await self._pending(preparation_ref, parent_run_id, request, requirement_key=requirement_key)

    async def _pending(self, preparation_ref: SourcePin, parent_run_id: str,
                       request: AuthorRequest, *, requirement_key: str | None = None) -> CapabilityResult:
        packet = self.sequence.objects.read_ref(preparation_ref)
        selected = self.sequence.objects._path('asset-scene-design',
            [packet['narrativeRef']['fingerprint'], packet['sceneId']])
        if SourcePin.model_validate(self.sequence.objects._read(selected)) != preparation_ref:
            raise ValueError('REFERENCE_PREPARATION_AUTHORITY_MISMATCH')
        known = await self.sequence._available(request.scope.work_id, query=preparation_ref.key,
            narrative_ref=SourcePin.model_validate(packet['narrativeRef']))
        keys = {a.content['specializedAsset'].get('requirementKey') for a in known}
        if requirement_key is not None:
            selected = self.sequence.objects._path('asset-scene-design',
                [packet['narrativeRef']['fingerprint'], packet['sceneId']])
            if (packet.get('schemaVersion') != 'specialized-asset-preparation-v1'
                    or (packet['workId'], packet['sceneId']) != (request.scope.work_id, request.scope.scene_id)
                    or not selected.exists()
                    or SourcePin.model_validate(self.sequence.objects._read(selected)) != preparation_ref):
                raise ValueError('REFERENCE_PREPARATION_AUTHORITY_MISMATCH')
            item = next((r for r in packet['requirements'] if r['requirementKey'] == requirement_key), None)
            if item is None or item.get('reuseAssetId') or item.get('referenceRequired') is not True:
                raise ValueError('REFERENCE_REQUIREMENT_NOT_PENDING')
            if requirement_key in keys:
                raise ValueError('REFERENCE_REQUIREMENT_ALREADY_ACCEPTED')
        else:
            item = next((r for r in packet['requirements'] if not r.get('reuseAssetId') and r['requirementKey'] not in keys), None)
        if item is None:
            # Missing/invalid existing adopted media needs recovery, never replacement.
            return self.wait_ref(ArtifactReference(owner='specialized-asset-preparation',
                artifact_ref=preparation_ref.key+':'+preparation_ref.fingerprint, version=1), 'EXISTING_ASSET_REFERENCE_RECOVERY')
        identity = parent_run_id+':asset-reference:'+item['requirementKey'][:24]
        try:
            prior = self.get(identity)
        except KeyError:
            prior = None
        if prior is not None and prior.preparation_ref != preparation_ref:
            identity += ':' + preparation_ref.fingerprint[:24]
        async with self.lock(identity):
            try:
                run = self.plugin.runtime.store.load(identity)
            except KeyError:
                run = self.plugin.runtime.create_run(work_id=packet['workId'], scene_id=packet['sceneId'],
                    run_id=identity, mode=self.plugin.runtime.store.load(parent_run_id).mode, workflow_id=WORKFLOW)
            if run.workflow_id != WORKFLOW or run.scope != RuntimeScope(work_id=packet['workId'], scene_id=packet['sceneId']):
                raise ValueError('REFERENCE_CHILD_IDENTITY_CONFLICT')
            try:
                self.get(identity)
            except KeyError:
                context = self.sequence.objects.put('asset-reference-author-context:'+identity,
                    packet.get('referenceAuthorContext') or dump_contract(request))
                record = ReferenceProductionRecord.seal(run_id=identity, scope=run.scope,
                    preparation_ref=preparation_ref, requirement_key=item['requirementKey'], author_context_ref=context)
                self.save(record)
        child = await self.resume(identity)
        if child.state == RuntimeState.SUCCEEDED:
            return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(self.get(identity).artifact_reference(),))
        child_ref = ArtifactReference(owner='runtime', artifact_ref=identity)
        if child.state in {RuntimeState.FAILED, RuntimeState.BLOCKED} and child.last_result:
            return child.last_result.model_copy(update={'artifact_refs': (*child.last_result.artifact_refs, child_ref)})
        preparation = ArtifactReference(owner='specialized-asset-preparation',
            artifact_ref=preparation_ref.key+':'+preparation_ref.fingerprint, version=1)
        return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL, external_ref=preparation,
            recovery_class=RecoveryClass.WAIT_EXTERNAL, artifact_refs=(preparation, child_ref))

    @staticmethod
    def wait_ref(ref: ArtifactReference, code: str) -> CapabilityResult:
        return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL, external_ref=ref,
            recovery_class=RecoveryClass.WAIT_EXTERNAL, artifact_refs=(ref,))

    def wait(self, value: ReferenceProductionRecord, code: str,
             category: DecisionCategory | None = None) -> CapabilityResult:
        if code and value.required_action != code:
            value = self.save(value, required_action=code)
        ref = value.artifact_reference()
        if category:
            needs_media = self.item(value)['referenceRequired']
            return CapabilityResult(status=ResultStatus.WAITING_EXTERNAL, external_ref=ref,
                recovery_class=RecoveryClass.USER_DECISION, artifact_refs=(ref,),
                user_decision=UserDecisionRequest(category=category, question=(
                    'Approve this exact reference image request, current quote and one-operation budget?'
                    if category == DecisionCategory.COST_APPROVAL else
                    'Adopt this retained, reviewed reference for its exact specialized asset design?'
                    if needs_media else 'Adopt this exact specialized text design without reference media?')))
        return self.wait_ref(ref, code)

    @staticmethod
    def success(value: ReferenceProductionRecord) -> CapabilityResult:
        return CapabilityResult(status=ResultStatus.SUCCEEDED, artifact_refs=(value.artifact_reference(),))

    def validate_frame(self, value: ReferenceProductionRecord, spec: FrameSpec) -> None:
        item = self.item(value)
        if not item['referenceRequired']:
            raise ValueError('THIS_ASSET_REQUIRES_NO_REFERENCE_MEDIA')
        design = SourcePin.model_validate(item['designRef'])
        if (spec.shot_id != 'asset-reference:'+value.requirement_key
                or spec.shot_fingerprint != design.fingerprint or spec.professional_sources):
            raise ValueError('REFERENCE_FRAME_DESIGN_AUTHORITY_MISMATCH')
        # professional_sources is the opt-in retained Still Knowledge mapping
        # contract, not a generic list of pins. Native provenance is this exact
        # selected preparation/design and sealed artwork, validated here.
        if spec.prompt_ir is None:
            raise ValueError('REFERENCE_FRAME_REQUIRES_EXISTING_PROMPT_IR')
        if item['assetType'] == 'CHARACTER' and {a.entity_key for a in spec.actors} != {item['subjectId']}:
            raise ValueError('REFERENCE_FRAME_CHARACTER_BINDING_MISMATCH')
        from drama_plugin.contracts.visual_prompt import VisualPromptIR
        ir = VisualPromptIR.model_validate(spec.prompt_ir)
        faces = {s.id: s.face.text for s in ir.subjects}
        if any(a.identity != faces.get(a.entity_key) for a in spec.actors):
            raise ValueError('REFERENCE_ARTWORK_IDENTITY_TEXT_DIVERGES')
        if spec.image_mode != item.get('referenceMode','text_to_image'):
            raise ValueError('REFERENCE_IMAGE_MODE_DIFFERS_FROM_SELECTED_REQUIREMENT')
        if spec.image_mode == 'image_to_image':
            if {r.asset_id for r in spec.references} != set(item.get('referenceAssetIds', [])):
                raise ValueError('REFERENCE_IMAGE_INPUT_SELECTION_MISMATCH')

    async def reference_inputs(self, value: ReferenceProductionRecord) -> tuple[Any, ...]:
        """Read accepted inputs only for an explicitly selected I2I requirement."""
        item = self.item(value)
        if item.get('referenceMode','text_to_image') != 'image_to_image':
            return ()
        from drama_plugin.visual.frame_request import Reference
        from drama_plugin.execution.media import atomic_write
        refs = []
        for asset_id in item['referenceAssetIds']:
            asset = await self.sequence.assets.get_asset(asset_id)
            if asset.work_id != value.scope.work_id or not self.sequence._proof(asset):
                raise ValueError('IMAGE_INPUT_REQUIRES_EXISTING_ADOPTED_ASSET')
            if len(asset.reference_media_ids) != 1:
                raise ValueError('EXACT_SINGLE_ASSET_REFERENCE_SELECTION_REQUIRED')
            media = await self.plugin.providers.media.get_media(asset.reference_media_ids[0])
            self.sequence._media_identity(media,value.scope.work_id)
            proof = await verify_media(self.plugin.providers.media,MediaIdentity.from_media(media),self.cache/'inputs')
            local = proof['cachePath']
            name = 'inline:'+proof['contentHash']
            receipt = self.cache/'inputs'/(proof['contentHash']+'.inline.json')
            atomic_write(receipt,canonical_json({'name':name,'content_hash':proof['contentHash'],
                'transport':'INLINE_BASE64','provider':'ark','mediaId':media.id}).encode())
            design = asset.content['specializedAsset']
            refs.append(Reference(entity_key=design['subjectId'] or design['stableIdentity'],
                kind='SCENE' if design['assetType']=='LOCATION' else design['assetType'],
                asset_id=asset.id,media_id=media.id,version=str(design['revision']),
                content_hash=proof['contentHash'],local_path=local,upload_name=name,
                uploaded_hash=proof['contentHash'],upload_receipt=str(receipt),
                facts=canonical_json(design['design']),state='Exact adopted reference',review='PASS'))
        return tuple(refs)

    async def supply_frame(self, run_id: str, frame: FrameSpec) -> ReferenceProductionRecord:
        async with self.lock(run_id):
            value = self.get(run_id)
            self.validate_frame(value, frame)
            # Historical artwork stays frozen. Both new Host and model supply
            # inherit the selected original through this same Target owner.
            if value.frame is not None:
                if compile_frame(frame) != value.frame:
                    raise ValueError('REFERENCE_FRAME_ALREADY_SEALED')
                return value
            from drama_plugin.professional_design.reference_design import inherit_design, verify_design_delivery
            item = await self.artwork_item(value)
            from drama_plugin.professional_design.reference_design import DesignCompletionRequired
            try:
                frame = inherit_design(frame, item)
            except DesignCompletionRequired as error:
                self.complete_design(value, error)
                return self.get(run_id)
            self.validate_frame(value, frame)
            if frame.image_mode == 'image_to_image':
                expected = await self.reference_inputs(value)
                keys = ('entity_key','kind','asset_id','media_id','version','content_hash')
                if [{k:getattr(r,k) for k in keys} for r in frame.references] != [{k:getattr(r,k) for k in keys} for r in expected]:
                    raise ValueError('REFERENCE_ADOPTED_INPUT_IDENTITY_CHANGED')
            compiled = compile_frame(frame)
            try:
                verify_design_delivery(compiled, item)
            except DesignCompletionRequired as error:
                self.complete_design(value, error)
                return self.get(run_id)
            return self.save(value, frame=compiled)

    async def revise_designs(self, preparation_ref: SourcePin,
                             designs: dict[str, dict[str, JsonValue]]) -> SourcePin:
        """Revise unadopted design originals, never a sealed request or paid run.

        Keys are exact old requirement fingerprints. No model/media call and no
        inherited spending; the existing pending path prepares new child runs.
        """
        from drama_plugin.professional_design.provenance import reject_model_metadata
        packet = self.sequence.objects.read_ref(preparation_ref)
        if packet.get('schemaVersion') != 'specialized-asset-preparation-v1' or not designs:
            raise ValueError('REFERENCE_DESIGN_REVISION_REQUIRED')
        work, scene = packet['workId'], packet['sceneId']
        lock = self.sequence._locks.setdefault('prepare:' + work, asyncio.Lock())
        async with lock, AsyncExitStack() as held:
            selected = self.sequence.objects._path('asset-scene-design',
                [packet['narrativeRef']['fingerprint'], scene])
            if SourcePin.model_validate(self.sequence.objects._read(selected)) != preparation_ref:
                raise ValueError('REFERENCE_PREPARATION_AUTHORITY_MISMATCH')
            items = {r['requirementKey']: r for r in packet['requirements']}
            if not set(designs) <= set(items):
                raise ValueError('REFERENCE_DESIGN_REVISION_SCOPE_MISMATCH')
            for key, design in designs.items():
                if items[key].get('reuseAssetId') or not items[key]['referenceRequired']:
                    raise ValueError('REFERENCE_REVISION_REQUIRES_PENDING_VISUAL_DESIGN')
                reject_model_metadata(design)
            with self.ledger.transaction() as db:
                run_ids = [r['index_key'] for r in db.execute(
                    'SELECT index_key FROM ledger_index WHERE index_type=? AND work_id=? AND scene_id=?',
                    (INDEX, work, scene))]
            for run_id in sorted(run_ids):
                await held.enter_async_context(self.lock(run_id))
                value = self.get(run_id)
                if value.preparation_ref != preparation_ref:
                    continue
                if value.asset_id or value.adoption_ref:
                    raise ValueError('REFERENCE_REVISION_CANNOT_REPLACE_ADOPTED_ASSET')
                if value.stage is not None:
                    failed_review = (value.receipt and value.receipt['status'] == 'COMPLETED'
                        and value.delivery and value.stage['attempts'][0]['review_status'] == 'FAIL')
                    not_created = value.receipt and value.receipt['status'] == 'NOT_CREATED'
                    if not (failed_review or not_created):
                        raise ValueError('REFERENCE_REVISION_IN_FLIGHT_OR_REVIEW_PENDING')
            # Include externally adopted records, not only these local children.
            available = await self.sequence._available(work, query=preparation_ref.key,
                narrative_ref=SourcePin.model_validate(packet['narrativeRef']))
            if any(a.content['specializedAsset'].get('requirementKey') in items for a in available):
                raise ValueError('REFERENCE_REVISION_CANNOT_REPLACE_ADOPTED_ASSET')
            changed = deepcopy(packet)
            for item in changed['requirements']:
                key = item['requirementKey']
                if key not in designs:
                    continue
                original = self.sequence.objects.read_ref(SourcePin.model_validate(item['designRef']))
                original['design'] = designs[key]
                pin = self.sequence.objects.put(item['designRef']['key'], original)
                item.update(design=designs[key], designRef=dump_contract(pin), requirementKey=pin.fingerprint)
            if changed == packet:
                return preparation_ref
            following = self.sequence.objects.put(preparation_ref.key, changed)
            with self.sequence.objects._writer():
                if SourcePin.model_validate(self.sequence.objects._read(selected)) != preparation_ref:
                    raise ValueError('REFERENCE_PREPARATION_AUTHORITY_MISMATCH')
                self.sequence.objects._write(selected, dump_contract(following))
            return following

    def complete_design(self, value: ReferenceProductionRecord, error: ValueError) -> CapabilityResult:
        # Existing author handoff, not a Runtime failure or user approval. Pins
        # and full author context already live in this record/preparation.
        return self.wait(value, 'HOST_COMPLETE_REFERENCE_DESIGN: ' + str(error) +
            '. Read specialized_assets.read_preparation using the parent result preparation ArtifactReference; '
            'use its referenceAuthorContext and selected originals to complete the '
            'affected design through Specialized Asset Design (Prop Design for props). '
            'Save the full replacement with specialized_assets.revise_reference_designs, '
            'then resume the parent creative Run to prepare the new reference. '
            'Complete this work in the current Host task; do not ask the user to write '
            'a Prompt or approve routine completion. Do not invent source facts.')

    async def ensure_design_delivery(self, value: ReferenceProductionRecord) -> ReferenceProductionRecord:
        """Fill an unapproved request from its original, without a paid author call.

        Ledger snapshots stay immutable. If source authorship is needed, hand it
        back to the Host; never make the user patch a Prompt. Approved/reserved
        requests keep their exact spending identity and existing recovery path.
        """
        from drama_plugin.professional_design.reference_design import (
            DesignCompletionRequired, inherit_design, verify_design_delivery)
        if value.frame is None:
            return value
        item = await self.artwork_item(value)
        try:
            verify_design_delivery(value.frame, item)
            return value
        except DesignCompletionRequired:
            if (value.stage is not None or value.cost_ref is not None
                    or self.plugin.runtime.store.load(value.run_id).state == RuntimeState.WAITING_USER
                    or self.decision(value, DecisionCategory.COST_APPROVAL) is not None):
                raise ValueError('REFERENCE_APPROVED_REQUEST_REQUIRES_EXISTING_RECOVERY')
        try:
            frame = inherit_design(FrameSpec.model_validate(value.frame['spec']), item)
            self.validate_frame(value, frame)
            compiled = compile_frame(frame)
            verify_design_delivery(compiled, item)
        except DesignCompletionRequired as error:
            self.complete_design(value, error)
            return self.get(value.run_id)
        return self.save(value, frame=compiled, quote=None, balance=None,
            execution_binding=None, budget=None, required_action='CURRENT_REFERENCE_QUOTE_REQUIRED')

    async def prepare(self, inputs: CapabilityInput) -> CapabilityResult:
        value = self.get(inputs.run_id)
        if value.frame is not None:
            value = await self.ensure_design_delivery(value)
            if (value.required_action or '').startswith('HOST_COMPLETE_REFERENCE_DESIGN:'):
                return self.wait(value, value.required_action or '')
            return self.success(value)
        item = await self.artwork_item(value)
        if not item['referenceRequired']:
            return self.success(value)
        from drama_plugin.professional_design.reference_design import DesignCompletionRequired, selected_leaves
        try:
            # Diagnose before invoking a reference artist. Preserve incomplete
            # originals so the Host has exact, resumable work rather than a crash.
            selected_leaves(item)
            author = self.plugin.professional_design.author
            method = getattr(author, 'design_asset_reference', None)
            if method is None:
                return self.wait(value, 'SPECIALIZED_REFERENCE_ARTWORK_REQUIRED')
            request = AuthorRequest.model_validate(self.sequence.objects.read_ref(value.author_context_ref))
            refs = await self.reference_inputs(value)
            frame = await method(request,item,reference_inputs=refs) if refs else await method(request,item)
            result = await self.supply_frame(inputs.run_id, FrameSpec.model_validate(frame))
            return self.success(result) if result.frame is not None else self.wait(result, result.required_action or '')
        except DesignCompletionRequired as error:
            return self.complete_design(self.get(inputs.run_id), error)

    async def quote_reference(self, run_id: str, *, quote: dict[str, Any], balance: dict[str, Any],
                              budget: float, execution_binding: dict[str, Any]) -> ReferenceProductionRecord:
        async with self.lock(run_id):
            value = self.get(run_id)
            if value.frame is None or value.stage is not None or value.cost_ref is not None:
                raise ValueError('UNRESERVED_COMPILED_REFERENCE_REQUIRED')
            following = await self.ensure_design_delivery(value)
            if following != value:
                # Return refreshed artwork to the Host for a request-bound quote.
                return following
            if (value.required_action or '').startswith('HOST_COMPLETE_REFERENCE_DESIGN:'):
                return value
            if self.plugin.runtime.store.load(run_id).state == RuntimeState.WAITING_USER:
                raise ValueError('REFERENCE_QUOTE_ALREADY_PRESENTED_FOR_DECISION')
            from drama_plugin.visual.execution import validate_binding
            validate_binding(value.frame, execution_binding)
            stage = still.new_stage(stage_id=run_id, authorization_ref='pending:'+value.fingerprint,
                budget_credits=budget, budget_unit=quote['unit'], frames=[value.frame], protected_targets=[])
            still._stage_gate(stage, value.frame, value.frame['request'], quote, balance)
            return self.save(value, quote=quote, balance=balance, budget=budget,
                budget_unit=quote['unit'], execution_binding=execution_binding)

    def decision(self, value: ReferenceProductionRecord, category: DecisionCategory) -> ArtifactReference | None:
        run = self.plugin.runtime.store.load(value.run_id)
        ref = next((r for r in (run.last_result.artifact_refs if run.last_result else ()) if r.owner == 'user-decision'), None)
        if ref is None:
            return None
        raw, scope, _ = self.ledger.get_artifact('user-decision', ref)
        record = UserDecisionRecord.model_validate(raw)
        if (not record.accepted or record.run_id != value.run_id or scope != value.scope
                or record.category != category or record.source_ref != value.artifact_reference()):
            raise ValueError('REFERENCE_EXACT_USER_DECISION_REQUIRED')
        return ref

    async def formal_scope(self, value: ReferenceProductionRecord) -> bool:
        """The existing Asset/import API requires its actual Work envelope.

        Target video native-scope authorization is a different contract. Do not
        forge a Shot/Package to import a reference or invent a Service Work alias.
        """
        try:
            work = await self.plugin.providers.memory.get_work(value.scope.work_id)
        except (ProviderError, httpx.HTTPError) as error:
            from drama_plugin.exceptions import RemoteServiceError
            if not isinstance(error,RemoteServiceError):
                if not self.plugin.native_task_persistence.enabled:
                    return False
                raise  # An unavailable read is not evidence of an absent Work.
            if isinstance(error,RemoteServiceError) and error.error_code != 'NOT_FOUND' and error.status_code != 404:
                raise
            request = AuthorRequest.model_validate(self.sequence.objects.read_ref(value.author_context_ref))
            if not request.source_refs or not self.plugin.native_task_persistence.enabled:
                return False
            # Same-ID business envelope, readback checked; no alias or Canon write.
            work = await self.plugin.native_task_persistence.persist(request.source_refs)
        return work.id == value.scope.work_id

    async def reserve(self, inputs: CapabilityInput) -> CapabilityResult:
        async with self.lock(inputs.run_id):
            value = self.get(inputs.run_id)
            if not self.item(value)['referenceRequired']:
                return self.success(value)
            if value.stage is not None:
                return self.success(value)
            value = await self.ensure_design_delivery(value)
            if (value.required_action or '').startswith('HOST_COMPLETE_REFERENCE_DESIGN:'):
                return self.wait(value, value.required_action or '')
            if not await self.formal_scope(value):
                return self.wait(value, 'FORMAL_ASSET_WORK_SCOPE_REQUIRED')
            if not value.quote or not value.balance or not value.execution_binding:
                return self.wait(value, 'CURRENT_REFERENCE_QUOTE_REQUIRED')
            if (approval := self.decision(value, DecisionCategory.COST_APPROVAL)) is None:
                return self.wait(value, '', DecisionCategory.COST_APPROVAL)
            assert value.frame is not None
            stage = still.new_stage(stage_id=value.run_id, authorization_ref=approval.artifact_ref,
                budget_credits=value.budget, budget_unit=value.budget_unit,
                frames=[value.frame], protected_targets=[])
            still.reserve(stage, value.frame['spec']['shot_id'], quote=value.quote, balance=value.balance,
                execution_binding=value.execution_binding)
            return self.success(self.save(value, stage=stage, cost_ref=approval))

    async def submit(self, inputs: CapabilityInput) -> CapabilityResult:
        async with self.lock(inputs.run_id):
            value = self.get(inputs.run_id)
            if not self.item(value)['referenceRequired']:
                return self.success(value)
            if value.receipt and value.receipt['status'] == 'COMPLETED':
                return self.success(value)
            assert value.stage is not None and value.frame is not None
            stage = deepcopy(value.stage)
            attempt = stage['attempts'][0]
            recovered = retained_receipt(self.cache, value.scope.work_id, attempt)
            if recovered is None:
                if attempt.get('submission_started'):
                    return self.wait(value, 'ARK_SYNCHRONOUS_SUBMISSION_UNKNOWN_RECOVER_SAME_OUTPUT')
                # Credential/capability/source failures are local, before uncertainty.
                self.item(value)
                from drama_plugin.visual.execution import validate_binding
                validate_binding(value.frame, attempt.get('execution_binding'))
                still.begin_submission(stage, attempt_id=attempt['attempt_id'])
                value = self.save(value, stage=stage)  # BEFORE transport, durable across restart.
                assert value.frame is not None
                try:
                    recovered = await submit_reserved(value.scope.work_id, attempt, value.frame, self.cache)
                except (httpx.HTTPError, ValueError):
                    return self.wait(value, 'ARK_SYNCHRONOUS_SUBMISSION_UNKNOWN_RECOVER_SAME_OUTPUT')
            status = recovered['status']
            if status == 'UNKNOWN':
                return self.wait(self.save(value, receipt=recovered), 'ARK_SYNCHRONOUS_SUBMISSION_UNKNOWN_RECOVER_SAME_OUTPUT')
            still.record_result(stage, attempt_id=attempt['attempt_id'], status=status,
                job_id=recovered.get('task_id'), output_hash=recovered.get('output_hash'),
                execution_receipt=recovered.get('correlation'), evidence='Retained Ark synchronous receipt')
            value = self.save(value, stage=stage, receipt=recovered)
            if status != 'COMPLETED':
                return CapabilityResult(status=ResultStatus.FAILED, code='REFERENCE_IMAGE_NOT_CREATED',
                    recovery_class=RecoveryClass.HARD_BLOCK, artifact_refs=(value.artifact_reference(),))
            return self.success(value)

    async def persist(self, inputs: CapabilityInput) -> CapabilityResult:
        async with self.lock(inputs.run_id):
            value = self.get(inputs.run_id)
            if not self.item(value)['referenceRequired']:
                return self.success(value)
            if value.delivery:
                return self.success(value)
            assert value.receipt and value.frame and value.stage
            item = self.item(value)
            output = value.receipt
            expected = MediaIdentity(value.scope.work_id, MediaType.IMAGE,
                'asset-reference:'+value.stage['attempts'][0]['attempt_id'], output['output_hash'],
                purpose=item['assetType']+'_REFERENCE')
            try:
                existing = await self.plugin.providers.media.list_media(work_id=expected.work_id,
                    media_type=MediaType.IMAGE, source_ref=expected.source_ref, purpose=expected.purpose, include_debug=True)
                if len(existing) > 1:
                    raise ValueError('REFERENCE_MEDIA_SOURCE_AMBIGUOUS')
                if existing:
                    expected = MediaIdentity(**{**expected.__dict__, 'media_id': existing[0].id})
                    delivery = await verify_media(self.plugin.providers.media, expected, self.cache)
                else:
                    delivery = await persist_media(self.plugin.providers.media, expected,
                        source=Path(output['output_path']), cache=self.cache,
                        content={'referenceProductionRef': dump_contract(value.artifact_reference()),
                            'designRef': item['designRef'], 'usageMode': 'RETAINED_REFERENCE',
                            'width': value.frame['template']['output_size'][0],
                            'height': value.frame['template']['output_size'][1]})
                if delivery.get('persistenceStatus') != 'VERIFIED':
                    raise ValueError('REFERENCE_FORMAL_READBACK_REQUIRED')
                streams = delivery['technical']['streams']
                sizes = {(s.get('width'), s.get('height')) for s in streams}
                if tuple(value.frame['template']['output_size']) not in sizes:
                    raise ValueError('REFERENCE_OUTPUT_DIMENSIONS_MISMATCH')
            except (httpx.HTTPError, ValueError, OSError, MediaImportSourceError):
                return self.wait(value, 'REFERENCE_PERSISTENCE_RECOVERY_SAME_OUTPUT')
            stage = deepcopy(value.stage)
            stage['attempts'][0].update(delivery=delivery, persistence_status='VERIFIED', technical_status='PASS')
            return self.success(self.save(value, stage=stage, delivery=delivery))

    async def review_reference(self, run_id: str, review: still.Review) -> ReferenceProductionRecord:
        async with self.lock(run_id):
            value = self.get(run_id)
            if not value.delivery:
                raise ValueError('REFERENCE_REVIEW_REQUIRES_FORMAL_MEDIA_READBACK')
            assert value.stage is not None
            stage = deepcopy(value.stage)
            if 'review' in stage['attempts'][0]:
                if stage['attempts'][0]['review'] != dump_contract(review):
                    raise ValueError('REFERENCE_REVIEW_ALREADY_RECORDED')
                return value
            still.record_review(stage, review)
            return self.save(value, stage=stage)

    async def review(self, inputs: CapabilityInput) -> CapabilityResult:
        value = self.get(inputs.run_id)
        if not self.item(value)['referenceRequired']:
            return self.success(value)
        assert value.stage is not None
        attempt = value.stage['attempts'][0]
        if not still.usable(attempt):
            if attempt.get('review_status') == 'FAIL':
                return CapabilityResult(status=ResultStatus.FAILED, code='REFERENCE_CONTENT_REJECTED',
                    recovery_class=RecoveryClass.HARD_BLOCK, artifact_refs=(value.artifact_reference(),))
            return self.wait(value, 'REFERENCE_VISUAL_REVIEW_REQUIRED')
        return self.success(value)

    async def adopt(self, inputs: CapabilityInput) -> CapabilityResult:
        async with self.lock(inputs.run_id):
            value = self.get(inputs.run_id)
            if value.adoption_ref:
                return self.success(value)
            if not await self.formal_scope(value):
                return self.wait(value, 'FORMAL_ASSET_WORK_SCOPE_REQUIRED')
            if (approval := self.decision(value, DecisionCategory.ADOPTION)) is None:
                return self.wait(value, '', DecisionCategory.ADOPTION)
            return self.success(self.save(value, adoption_ref=approval))

    async def register(self, inputs: CapabilityInput) -> CapabilityResult:
        async with self.lock(inputs.run_id):
            value = self.get(inputs.run_id)
            if value.asset_id:
                await self.sequence.assets.get_asset(value.asset_id)
                return self.success(value)
            item = self.item(value)
            if not value.adoption_ref or item['referenceRequired'] and (
                    not value.delivery or not value.stage or not still.usable(value.stage['attempts'][0])):
                raise ValueError('REFERENCE_ADOPTION_REQUIRES_REVIEWED_PERSISTED_MEDIA')
            media_ids = (value.delivery['mediaId'],) if value.delivery else ()
            if value.delivery:
                formal = await self.plugin.providers.media.get_media(value.delivery['mediaId'])
                MediaIdentity(value.scope.work_id, MediaType.IMAGE, value.delivery['sourceRef'],
                    value.delivery['contentHash'], purpose=item['assetType']+'_REFERENCE',
                    media_id=value.delivery['mediaId']).check(formal)
            # The complete run/proof remains inside the retained original. Keep
            # the index key bounded so its SourcePin fits the formal SQL ref.
            original = self.sequence.objects.put('asset-reference-adoption:'+sha256_canonical(inputs.run_id),
                {'decision': 'ADOPT', 'workId': value.scope.work_id,
                    'subjectFingerprint': item['designRef']['fingerprint'],
                    'referenceMediaIds': list(media_ids),
                    'referenceContentHash': value.delivery['contentHash'] if value.delivery else None,
                    'reviewOriginal': still.current_review(value.stage['attempts'][0]) if value.stage else None,
                    'referenceProductionRef': dump_contract(value.artifact_reference()),
                    'userDecisionRef': dump_contract(value.adoption_ref)})
            asset = await self.sequence.accept(value.preparation_ref, value.requirement_key,
                adoption_ref=original, reference_media_ids=media_ids)
            return self.success(self.save(value, asset_id=asset.id))

    async def resume(self, run_id: str) -> RuntimeRun:
        # Older checkpoints classified a local import allowlist error as terminal.
        # Recover only that exact completed reference at its persistence step;
        # the immutable submission receipt and provider step are never replayed.
        async with self.plugin.runtime.store.lock(run_id):
            prior = self.plugin.runtime.store.load(run_id)
            failed = prior.last_result
            if (prior.workflow_id == WORKFLOW and prior.state == RuntimeState.FAILED
                    and prior.cursor == 3 and failed is not None
                    and failed.code == 'CAPABILITY_EXECUTION_ERROR'
                    and failed.failure_stage == 'CAPABILITY_EXECUTION'
                    and failed.exception_type == 'MediaImportSourceError'
                    and prior.executing_action == reference_workflow().steps[3]):
                value = self.get(run_id)
                if (not value.receipt or value.receipt.get('status') != 'COMPLETED'
                        or not value.stage or value.stage['attempts'][0]['status'] != 'COMPLETED'
                        or value.receipt['output_hash'] != value.stage['attempts'][0]['output_hash']):
                    raise ValueError('REFERENCE_IMPORT_RECOVERY_REQUIRES_SAME_COMPLETED_OUTPUT')
                evidence = {'failedRun': dump_contract(prior),
                    'completedReferenceRef': dump_contract(value.artifact_reference()),
                    'outputHash': value.receipt['output_hash'], 'providerResubmitted': False}
                recovery = self.sequence.objects.put(f'{run_id}:import-recovery:{prior.revision}', evidence)
                result = await self.persist(CapabilityInput(run_id=run_id,
                    operation_id=f'{run_id}:3', scope=prior.scope))
                succeeded = result.status == ResultStatus.SUCCEEDED
                if succeeded:
                    value = self.get(run_id)
                    delivery = {**value.delivery, 'importRecoveryRef': dump_contract(recovery)}
                    stage = deepcopy(value.stage)
                    stage['attempts'][0]['delivery'] = delivery
                    result = self.success(self.save(value, delivery=delivery, stage=stage))
                following = RuntimeRun.model_validate({**prior.model_dump(),
                    'state': RuntimeState.READY if succeeded else RuntimeState.WAITING_EXTERNAL,
                    'cursor': 4 if succeeded else 3, 'revision': prior.revision + 1,
                    'step_attempts': 0 if succeeded else prior.step_attempts,
                    'last_result': result, 'wait_reason': None if succeeded else 'EXTERNAL_RESULT_PENDING',
                    'executing_action': None if succeeded else prior.executing_action})
                self.plugin.runtime.store.save(following, expected_revision=prior.revision)
            elif (prior.workflow_id == WORKFLOW and prior.state == RuntimeState.FAILED
                    and prior.cursor == 6 and failed is not None
                    and failed.code == 'CAPABILITY_EXECUTION_ERROR'
                    and failed.failure_stage == 'CAPABILITY_EXECUTION'
                    and failed.exception_type == 'RemoteServiceError'
                    and prior.executing_action == reference_workflow().steps[6]
                    and self.plugin.film_storage is not None):
                value = self.get(run_id)
                if (value.asset_id is not None or not value.adoption_ref or not value.delivery
                        or not value.stage or not still.usable(value.stage['attempts'][0])):
                    return prior
                rows = await self.plugin.film_storage.client.query('drama_asset',
                    {'media_id': value.delivery['mediaId']}, 1)
                if (len(rows) != 1 or rows[0]['work_id'] != value.scope.work_id
                        or rows[0]['state'] != 'CANDIDATE' or rows[0].get('design_media_id') is not None
                        or rows[0]['identity_key'] != 'file:' + value.delivery['mediaId']):
                    return prior
                recovery = self.sequence.objects.put(f'{run_id}:registration-recovery:{prior.revision}',
                    {'failedRun': dump_contract(prior), 'adoptedReferenceRef': dump_contract(value.artifact_reference()),
                        'candidateIndexId': rows[0]['id'], 'providerResubmitted': False})
                result = await self.register(CapabilityInput(run_id=run_id,
                    operation_id=f'{run_id}:6', scope=prior.scope))
                if result.status != ResultStatus.SUCCEEDED:
                    return prior
                value = self.get(run_id)
                delivery = {**value.delivery, 'registrationRecoveryRef': dump_contract(recovery)}
                stage = deepcopy(value.stage); stage['attempts'][0]['delivery'] = delivery
                result = self.success(self.save(value, delivery=delivery, stage=stage))
                following = RuntimeRun.model_validate({**prior.model_dump(), 'state': RuntimeState.READY,
                    'cursor': 7, 'revision': prior.revision + 1, 'step_attempts': 0,
                    'last_result': result, 'wait_reason': None, 'executing_action': None})
                self.plugin.runtime.store.save(following, expected_revision=prior.revision)
        run = await self.plugin.runtime.recover_run(run_id)
        if run.workflow_id != WORKFLOW:
            raise ValueError('SPECIALIZED_REFERENCE_RUN_REQUIRED')
        if run.state == RuntimeState.WAITING_EXTERNAL:
            key = reference_workflow().steps[run.cursor].capability_key
            assert key and run.last_result and run.last_result.external_ref
            result = await self.plugin.runtime.executor.execute(key, CapabilityInput(
                run_id=run_id, operation_id=f'{run_id}:{run.cursor}', scope=run.scope))
            await self.plugin.runtime.record_external_result(run_id, external_ref=run.last_result.external_ref, result=result)
        return await self.plugin.runtime.run(run_id)


def register_reference_tools(registry: Any, owner: TargetReferenceProduction | None) -> None:
    from drama_plugin.tools.catalog import _domain_tool
    def target() -> TargetReferenceProduction:
        if owner is None:
            from drama_plugin.exceptions import ConfigurationError
            raise ConfigurationError('Target reference production requires configured durable ProductionLedger')
        return owner
    async def read_reference(run_id: str) -> ReferenceProductionRecord:
        return target().get(run_id)
    async def frame_reference(run_id: str, frame: FrameSpec) -> ReferenceProductionRecord:
        return await target().supply_frame(run_id, frame)
    async def revise_reference_designs(preparation_ref: SourcePin,
                                       designs: dict[str, dict[str, JsonValue]]) -> SourcePin:
        return await target().revise_designs(preparation_ref, designs)
    async def quote_reference(run_id: str, quote: dict[str, Any], balance: dict[str, Any],
                              budget: float, execution_binding: dict[str, Any]) -> ReferenceProductionRecord:
        return await target().quote_reference(run_id, quote=quote, balance=balance,
            budget=budget, execution_binding=execution_binding)
    async def review_reference(run_id: str, review: still.Review) -> ReferenceProductionRecord:
        return await target().review_reference(run_id, review)
    async def resume_reference(run_id: str) -> RuntimeRun:
        return await target().resume(run_id)
    async def decide_reference(run_id: str, decision_id: str, accepted: bool,
                               source_ref: ArtifactReference) -> RuntimeRun:
        current = target()
        if current.plugin.runtime.store.load(run_id).workflow_id != WORKFLOW:
            raise ValueError('SPECIALIZED_REFERENCE_RUN_REQUIRED')
        return await current.plugin.decide_target_run(run_id, decision_id=decision_id,
            accepted=accepted, source_ref=source_ref)
    for name, handler, result, required in (
        ('read_reference', read_reference, ReferenceProductionRecord, {'run_id': str}),
        ('frame_reference', frame_reference, ReferenceProductionRecord, {'run_id': str, 'frame': FrameSpec}),
        ('revise_reference_designs', revise_reference_designs, SourcePin,
            {'preparation_ref': SourcePin, 'designs': dict[str, dict[str, JsonValue]]}),
        ('quote_reference', quote_reference, ReferenceProductionRecord, {'run_id': str, 'quote': dict, 'balance': dict, 'budget': float, 'execution_binding': dict}),
        ('review_reference', review_reference, ReferenceProductionRecord, {'run_id': str, 'review': still.Review}),
        ('resume_reference', resume_reference, None, {'run_id': str}),
        ('decide_reference', decide_reference, None, {'run_id': str, 'decision_id': str, 'accepted': bool, 'source_ref': ArtifactReference})):
        from drama_plugin.runtime.contracts import RuntimeRun
        registry.register(_domain_tool('specialized_assets.'+name,
            'Target retained reference production: '+name+'. No raw-prompt or automatic adoption bypass.',
            handler, result or RuntimeRun, required=required))
