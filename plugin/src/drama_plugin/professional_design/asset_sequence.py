"""Narrative-order asset preparation, owned by Specialized Asset Design.

Originals use the existing creative object store. Accepted versions use AssetProvider.
This owner never generates media, grants spending, or drives a second Runtime.
Missing references are resumable asset-resolution work, not a missing-asset hard Gate.
"""
from __future__ import annotations

from typing import Any, Literal, Protocol, TYPE_CHECKING, Self
import asyncio
from pydantic import Field, JsonValue, model_validator
from drama_plugin.contracts.base import ContractModel, dump_contract, sha256_canonical
from drama_plugin.contracts.asset import Asset, AssetType
from drama_plugin.contracts.media import Media
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.creative_engine.contracts import AuthorRequest, Authority, CanonDraft
from drama_plugin.creative_engine.author_projection import subjects
from drama_plugin.film.contracts import FilmCanon
from drama_plugin.runtime.contracts import ArtifactReference
from drama_plugin.production.contracts import SourceDomain

if TYPE_CHECKING:
    from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
    from drama_plugin.providers.base import AssetProvider, MediaProvider
    from drama_plugin.film_storage.storage import FilmStorage


class AssetChoice(ContractModel):
    """Artist selects supplied ordinals; identity and lineage are system-owned."""
    asset_type: Literal['CHARACTER', 'LOCATION', 'COSTUME', 'PROP', 'OTHER']
    name: str = Field(min_length=1)
    design: dict[str, JsonValue] = Field(min_length=1)
    subject_selection: int | None = Field(default=None, ge=0)
    reuse_selection: int | None = Field(default=None, ge=0)
    variant_reason: str | None = Field(default=None, min_length=1)
    reference_role: Literal['BASELINE', 'SUPPLEMENT'] = 'BASELINE'
    reference_required: bool = True
    reference_mode: Literal['text_to_image', 'image_to_image'] = 'text_to_image'
    reference_selections: tuple[int, ...] = Field(default=(), max_length=3)

    @model_validator(mode='after')
    def character_owner(self) -> Self:
        if self.asset_type in {'CHARACTER', 'COSTUME'} and self.subject_selection is None:
            raise ValueError('ASSET_SUBJECT_SELECTION_REQUIRED')
        if self.asset_type == 'CHARACTER' and not self.reference_required:
            raise ValueError('CHARACTER_IDENTITY_REQUIRES_VISUAL_REFERENCE')
        if self.reference_selections and self.reference_mode != 'image_to_image':
            raise ValueError('IMAGE_INPUTS_REQUIRE_EXPLICIT_IMAGE_TO_IMAGE')
        return self


class SceneAssetDraft(ContractModel):
    assets: tuple[AssetChoice, ...] = ()
    rationale: str = Field(min_length=1)


class AssetAuthor(Protocol):
    async def design_assets(self, request: AuthorRequest) -> SceneAssetDraft: ...


class AssetPreparationPending(Exception):
    def __init__(self, ref: SourcePin):
        self.ref = ref
        super().__init__('SPECIALIZED_ASSET_PREPARATION_PENDING')

    def runtime_ref(self) -> ArtifactReference:
        return ArtifactReference(owner='specialized-asset-preparation',
            artifact_ref=self.ref.key + ':' + self.ref.fingerprint, version=1)


def adopted_asset_original(value, name, read_pin) -> dict[str, Any]:
    """Read the exact local or Service-retained original, never a current head."""
    from drama_plugin.director import DirectorError
    ref = SourcePin.model_validate(value[name + 'Ref'])
    try:
        return read_pin(ref)
    except DirectorError:
        raw = value.get(name + 'Original')
        if not isinstance(raw, dict) or sha256_canonical(raw) != ref.fingerprint:
            raise
        return raw


def adopted_asset_proof(asset: Asset, read_original) -> bool:
    """Same retained adoption proof for assembly and its frozen consumers."""
    value = asset.content.get('specializedAsset')
    if not isinstance(value, dict) or value.get('state') != 'ADOPTED':
        return False
    if asset.asset_type in {AssetType.STANDARD_FACE, AssetType.MASTER_CHARACTER_CARD}:
        return False
    if value.get('filmStorageValidated') is True:
        # V2 retains the complete concrete design as a verified Markdown file
        # and small original adoption/source pins, rather than copying Package
        # and Scene snapshots into the Asset row. The authoritative Service
        # compatibility view supplies only the exact registered adopted version.
        return bool(value.get('designMediaId') and value.get('designRef') and value.get('adoptionRef')
            and (asset.asset_type!=AssetType.CHARACTER or value.get('subjectId') is not None)
            and value.get('design') and asset.reference_media_ids)
    try:
        review = read_original(value, 'adoption')
        original = read_original(value, 'design')
    except (ValueError, KeyError, OSError):
        return False
    return (review.get('decision') in {'APPROVE', 'ADOPT'}
        and review.get('workId') == asset.work_id
        and review.get('subjectFingerprint') == sha256_canonical(original)
        and all(value.get(k) == v for k, v in original.items())
        and asset.asset_type == original.get('assetType')
        and review.get('referenceMediaIds', []) == asset.reference_media_ids)


class SpecializedAssetSequence:
    def __init__(self, objects: DirectorArtifactStore, assets: AssetProvider, media: MediaProvider):
        self.objects, self.assets, self.media = objects, assets, media
        self._locks: dict[str, asyncio.Lock] = {}
        self.film_storage: FilmStorage | None = None
        self.reference_production: Any = None

    def bind_film(self, work_id: str, canon: FilmCanon, *, source_ref: ArtifactReference,
                  screenplay_ref: SourcePin | None = None, fresh_baseline: bool = False) -> SourcePin:
        """Bind selected art without changing an older Run's narrative selection.

        A fresh baseline is an explicit Host choice, not a character variation.
        Its immutable narrative pin also scopes its asset identities; callers
        retain and pass that exact pin to prepare. Legacy selection is unchanged.
        """
        material: dict[str, Any] = {'schemaVersion': 'specialized-asset-narrative-v1', 'workId': work_id,
            'sourceRef': dump_contract(source_ref), 'canon': dump_contract(canon)}
        if fresh_baseline:
            material['freshBaseline'] = True
        scene_refs = {}
        if screenplay_ref:
            packet = self.objects.read_ref(screenplay_ref)
            for row in packet.get('selectedSceneScreenplays', []):
                body = row['screenplay']
                if body['workId'] != work_id or body['sceneId'] not in {s.scene_id for s in canon.scenes}:
                    raise ValueError('ASSET_SCENE_SCREENPLAY_SCOPE_MISMATCH')
                scene_refs[body['sceneId']] = dump_contract(self.objects.put('asset-scene-screenplay:' + body['sceneId'], row))
        material['sceneScreenplayRefs'] = scene_refs
        ref = self.objects.put('specialized-asset-narrative:' + work_id, material)
        if fresh_baseline:
            return ref
        path = self.objects._path('asset-narrative', [work_id, sha256_canonical(canon.script)])
        with self.objects._writer():
            if path.exists():
                old = SourcePin.model_validate(self.objects._read(path))
                if self.objects.read_ref(old)['canon'] != material['canon']:
                    raise ValueError('ASSET_NARRATIVE_SELECTION_CONFLICT')
                return old
            self.objects._write(path, dump_contract(ref))
        return ref

    @staticmethod
    def _fixed_narrative(request: AuthorRequest) -> SourcePin | None:
        """Only retained system bindings select a family, never model prose."""
        context = request.professional_context or {}
        pins = []
        sequence = context.get('assetSequence')
        if isinstance(sequence, dict) and sequence.get('narrativeRef') is not None:
            pins.append(SourcePin.model_validate(sequence['narrativeRef']))
        rows = context.get('currentDesigns', [])
        if not isinstance(rows, list):
            raise ValueError('ASSET_NARRATIVE_BINDING_CONTEXT_MISMATCH')
        upstream = []
        for row in rows:
            facts = row.get('facts') if isinstance(row, dict) else None
            if isinstance(facts, dict):
                value = facts.get('assetNarrativeRef')
                if value is not None:
                    # Scene/Work originals contribute creative meaning. Their
                    # historical asset family must not replace this Shot's
                    # explicitly selected system binding.
                    target = pins if facts.get('scope') == request.scope.model_dump(mode='json', by_alias=True) else upstream
                    target.append(SourcePin.model_validate(value))
        if not pins:
            pins = upstream
        if len({(pin.key, pin.kind, pin.fingerprint) for pin in pins}) > 1:
            raise ValueError('ASSET_NARRATIVE_BINDING_CONFLICT')
        return pins[0] if pins else None

    def selected(self, request: AuthorRequest) -> SourcePin | None:
        if fixed := self._fixed_narrative(request):
            self._narrative(fixed, request)
            return fixed
        if request.canon is None:
            return None
        path = self.objects._path('asset-narrative', [request.scope.work_id,
            sha256_canonical(request.canon.script)])
        if not path.exists():
            # Historical partial Canon has no provable complete scene inventory.
            # Do not manufacture debut/lineage or rewrite historical adoption.
            return None
        return SourcePin.model_validate(self.objects._read(path))

    def _narrative(self, ref: SourcePin, request: AuthorRequest) -> FilmCanon:
        raw = self.objects.read_ref(ref)
        if raw.get('schemaVersion') != 'specialized-asset-narrative-v1' or raw['workId'] != request.scope.work_id:
            raise ValueError('ASSET_NARRATIVE_SCOPE_MISMATCH')
        canon = FilmCanon.model_validate(raw['canon'])
        scene = next((s.scene for s in canon.scenes if s.scene_id == request.scope.scene_id), None)
        if (request.canon is None or canon.work != request.canon.work
                or canon.script != request.canon.script or scene != request.canon.scene):
            raise ValueError('ASSET_NARRATIVE_CANON_MISMATCH')
        return canon

    def _proof(self, asset: Asset) -> bool:
        return adopted_asset_proof(asset, self._original)

    def _original(self, value: dict[str, Any], name: str) -> dict[str, Any]:
        """Service-held exact originals survive loss of a local discovery cache."""
        original = adopted_asset_original(value, name, self.objects.read_ref)
        # Professional bindings keep pins, not duplicate original bodies. Retain
        # restored evidence for their later consumers without changing adoption.
        self.objects.put(value[name + 'Ref']['key'], original)
        return original

    def _fresh(self, ref: SourcePin | None) -> bool:
        return bool(ref is not None and self.objects.read_ref(ref).get('freshBaseline') is True)

    def _in_family(self, asset: Asset, ref: SourcePin | None) -> bool:
        value = asset.content.get('specializedAsset', asset.content)
        stored = value.get('narrativeRef') if isinstance(value, dict) else None
        if self._fresh(ref):
            assert ref is not None
            return stored == dump_contract(ref)
        # Fresh roots carry a separate native namespace. Historical Service-only
        # rows need not have their narrative original cached locally, so do not
        # make legacy discovery depend on reading that unrelated original.
        identity = value.get('stableIdentity', '') if isinstance(value, dict) else ''
        return not str(identity).startswith(('specialized-character:fresh:', 'specialized-asset:fresh:'))

    async def _available(self, work_id: str, *, query: str | None = None,
                         narrative_ref: SourcePin | None = None) -> list[Asset]:
        result = []
        storage=getattr(self,'film_storage',None)
        if storage is not None:
            rows={}
            for kind in ('CHARACTER','LOCATION','COSTUME','PROP','OTHER'):
                for row in await storage.client.query('drama_asset',{'work_id':work_id,'asset_type':kind,'state':'ADOPTED'},100):
                    rows[row['id']]=await self.assets.get_asset(row['id'])
        else:
            rows = {asset.id: asset for asset in await self.assets.list_assets()}
        if query and storage is None:
            # Service's global list is bounded; an unrelated Work must not hide
            # an adopted version and cause repeat creation. Search exact pins.
            rows.update({asset.id: asset for asset in await self.assets.search_assets(query)})
        for asset in rows.values():
            if asset.work_id != work_id:
                continue
            if asset.asset_type in {AssetType.STANDARD_FACE, AssetType.MASTER_CHARACTER_CARD}:
                continue
            if not self._in_family(asset, narrative_ref):
                continue
            if self._proof(asset):
                result.append(asset)
            elif isinstance(asset.content.get('specializedAsset'), dict) and asset.content['specializedAsset'].get('state') == 'ADOPTED':
                raise ValueError('ASSET_ADOPTION_PROOF_INTEGRITY_MISMATCH')
            elif 'specializedAsset' not in asset.content:
                # Exact historical evidence only. Never match a display name or
                # promote a board/template merely because it is in the library.
                value = asset.content
                if value.get('state') != 'ADOPTED' or not {'designRef','adoptionRef'} <= value.keys():
                    continue
                original, review = self._original(value, 'design'), self._original(value, 'adoption')
                subject = original.get('subjectId', original.get('characterId', original.get('characterIdentity')))
                if (review.get('decision') not in {'APPROVE','ADOPT'} or review.get('workId') != work_id
                        or review.get('subjectFingerprint') != sha256_canonical(original)
                        or review.get('referenceMediaIds', []) != asset.reference_media_ids
                        or asset.asset_type not in {'CHARACTER','COSTUME','LOCATION','PROP','OTHER'}
                        or asset.asset_type == 'CHARACTER' and not isinstance(subject, str)):
                    continue
                identity = (self._character(work_id, str(subject),
                    narrative_ref.fingerprint if self._fresh(narrative_ref) and narrative_ref else None) if asset.asset_type == 'CHARACTER'
                    else original.get('stableIdentity'))
                if not identity or not isinstance(original.get('design'), dict):
                    continue
                normalized = {**value, 'assetType': asset.asset_type.value, 'subjectId': subject,
                    'stableIdentity': identity, 'design': original['design'], 'name': asset.name,
                    'revision': original.get('revision'), 'establishedSceneId': original.get('establishedSceneId', asset.scene_id),
                    'requirementKey': value.get('requirementKey', SourcePin.model_validate(value['designRef']).fingerprint),
                    'lineageStatus': 'PROVEN_EXISTING_ASSET', 'inheritedFromAssetId': original.get('inheritedFromAssetId'),
                    'identityRootAssetId': original.get('identityRootAssetId')}
                # A read projection only; original Asset and adoption stay intact.
                result.append(asset.model_copy(update={'content': {'specializedAsset': normalized}}))
        return result

    @staticmethod
    def _character(work_id: str, subject_id: str, family: str | None = None) -> str:
        identity = [work_id, subject_id]
        if family is not None:
            identity.append(family)
        return 'specialized-character:' + ('fresh:' if family is not None else '') + sha256_canonical(identity)

    def _latest(self, assets: list[Asset], identity: str) -> Asset | None:
        from .reference_roles import reference_role
        matches = [a for a in assets if a.content['specializedAsset']['stableIdentity'] == identity
                   and reference_role(self, a) == 'BASELINE']
        revisions = [a.content['specializedAsset']['revision'] for a in matches]
        if len(set(revisions)) != len(revisions):
            raise ValueError('ASSET_ACCEPTED_VERSION_AMBIGUOUS')
        return max(matches, key=lambda a: a.content['specializedAsset']['revision'] or 0, default=None)

    async def prepare(self, request: AuthorRequest, author: AssetAuthor, *,
                      narrative_ref: SourcePin | None = None) -> AuthorRequest:
        async with self._locks.setdefault('prepare:' + request.scope.work_id, asyncio.Lock()):
            fixed = self._fixed_narrative(request)
            if narrative_ref is not None and fixed is not None and narrative_ref != fixed:
                raise ValueError('ASSET_NARRATIVE_BINDING_CONFLICT')
            return await self._prepare(request, author, narrative_ref=narrative_ref)

    def candidate_parent(self, preparation_ref: SourcePin) -> SourcePin | None:
        """Recognize a source-bound review candidate without selecting it."""
        packet = self.objects.read_ref(preparation_ref)
        if packet.get('schemaVersion') != 'specialized-asset-preparation-v1':
            raise ValueError('ASSET_PREPARATION_REQUIRED')
        path = self.objects._path('asset-scene-design', [packet['narrativeRef']['fingerprint'], packet['sceneId']])
        if not path.exists():
            raise ValueError('ASSET_PREPARATION_NOT_SELECTED')
        selected = SourcePin.model_validate(self.objects._read(path))
        if selected == preparation_ref:
            return None
        if self._preparation_descends(selected, preparation_ref):
            # A frozen production input remains readable after another exact
            # reference adoption updated the same Scene's preparation.
            return selected
        context = packet.get('referenceAuthorContext', {})
        source = context.get('professionalContext', {}).get('assetPreparation', {}).get('revisionSourceRef')
        # AuthorRequest aliases are camelCase; tolerate its retained native view.
        if source is None:
            source = context.get('professional_context', {}).get('assetPreparation', {}).get('revisionSourceRef')
        source_ref = SourcePin.model_validate(source) if source is not None else None
        parent = self.objects.read_ref(selected)
        if (source_ref is None or not self._preparation_descends(selected, source_ref)
                or source not in packet.get('professionalBasisRefs', [])
                or any(parent.get(k) != packet.get(k) for k in ('schemaVersion', 'workId', 'sceneId', 'narrativeRef'))
                or not context.get('revision')):
            raise ValueError('ASSET_PREPARATION_NOT_SELECTED')
        return selected

    def _preparation_descends(self, selected: SourcePin, ancestor: SourcePin,
                             seen: frozenset[str] = frozenset()) -> bool:
        if selected == ancestor:
            return True
        if selected.fingerprint in seen or len(seen) >= 32:
            return False
        packet, basis = self.objects.read_ref(selected), self.objects.read_ref(ancestor)
        if any(packet.get(k) != basis.get(k) for k in ('schemaVersion', 'workId', 'sceneId', 'narrativeRef')):
            return False
        for raw in packet.get('professionalBasisRefs', []):
            if isinstance(raw, dict) and str(raw.get('key', '')).startswith('specialized-asset-preparation:'):
                parent = SourcePin.model_validate(raw)
                if self._preparation_descends(parent, ancestor, seen | {selected.fingerprint}):
                    return True
        return False

    def _reference_requirement_selection(self, preparation_ref: SourcePin, item: dict[str, Any]):
        packet = self.objects.read_ref(preparation_ref)
        path = self.objects._path('asset-scene-design', [packet['narrativeRef']['fingerprint'], packet['sceneId']])
        selected = SourcePin.model_validate(self.objects._read(path))
        current = self.objects.read_ref(selected)
        rows = list(current['requirements'])
        matches = [i for i, row in enumerate(rows) if row['stableIdentity'] == item['stableIdentity']]
        if len(matches) != 1:
            raise ValueError('ASSET_REFERENCE_SELECTION_IDENTITY_MISMATCH')
        index = matches[0]
        if rows[index] == item:
            return path, selected, current, rows, index
        # The candidate must revise the current requirement or its proven
        # ancestor, never silently replace an independently selected revision.
        context = packet.get('referenceAuthorContext', {})
        basis = context.get('professionalContext', context.get('professional_context', {}))
        source = basis.get('assetPreparation', {}).get('revisionSourceRef')
        if not source or not item.get('inheritedFromAssetId'):
            raise ValueError('ASSET_REFERENCE_SELECTION_CONFLICT')
        parent = self.objects.read_ref(SourcePin.model_validate(source))
        baseline = [row for row in parent['requirements'] if row['stableIdentity'] == item['stableIdentity']]
        if len(baseline) != 1 or rows[index] != baseline[0]:
            raise ValueError('ASSET_REFERENCE_SELECTION_CONFLICT')
        return path, selected, current, rows, index

    def _select_reference_requirement(self, preparation_ref: SourcePin, item: dict[str, Any]) -> None:
        """Merge only the just-adopted requirement; keep every other selected original."""
        path, selected, current, rows, index = self._reference_requirement_selection(preparation_ref, item)
        if rows[index] == item:
            return
        rows[index] = item
        bases = list(current.get('professionalBasisRefs', []))
        for pin in (selected, preparation_ref):
            raw = dump_contract(pin)
            if raw not in bases:
                bases.append(raw)
        revised = {**current, 'requirements': rows, 'professionalBasisRefs': bases}
        ref = self.objects.put('specialized-asset-preparation:' + sha256_canonical(revised), revised)
        with self.objects._writer():
            if SourcePin.model_validate(self.objects._read(path)) != selected:
                raise ValueError('ASSET_PREPARATION_SELECTION_CHANGED')
            self.objects._write(path, dump_contract(ref))

    async def revise_candidate(self, request: AuthorRequest, author: AssetAuthor, *,
                               preparation_ref: SourcePin, asset_ids: tuple[str, ...]) -> SourcePin:
        """Reassess selected accepted proofs through the existing formal author.

        This creates an immutable candidate only. The active preparation index,
        accepted assets and selected screenplay remain untouched.
        """
        async with self._locks.setdefault('prepare:' + request.scope.work_id, asyncio.Lock()):
            if (not asset_ids or len(set(asset_ids)) != len(asset_ids) or request.revision is None
                    or request.revision.owner != Authority.PROFESSIONAL):
                raise ValueError('EXPLICIT_ASSET_REVISION_REQUIRED')
            packet = self.objects.read_ref(preparation_ref)
            if self.candidate_parent(preparation_ref) is not None:
                raise ValueError('SELECTED_ASSET_PREPARATION_REQUIRED')
            ref = SourcePin.model_validate(packet['narrativeRef'])
            fixed = self._fixed_narrative(request)
            if fixed is not None and fixed != ref:
                raise ValueError('ASSET_NARRATIVE_BINDING_CONFLICT')
            canon = self._narrative(ref, request)
            if (packet['workId'], packet['sceneId']) != (request.scope.work_id, request.scope.scene_id):
                raise ValueError('ASSET_REVISION_SCOPE_MISMATCH')
            parents = [await self.assets.get_asset(identity) for identity in asset_ids]
            requirements = packet['requirements']
            for asset in parents:
                value = asset.content.get('specializedAsset', {})
                if (asset.work_id != request.scope.work_id or not self._proof(asset) or not self._in_family(asset, ref)
                        or not any(r.get('reuseAssetId') == asset.id or r.get('requirementKey') == value.get('requirementKey')
                            for r in requirements)):
                    raise ValueError('ASSET_REVISION_ACCEPTED_PARENT_REQUIRED')
            assert request.canon is not None
            selected_subjects = {a.content['specializedAsset']['subjectId'] for a in parents if a.asset_type == AssetType.CHARACTER}
            roster = [s for s in subjects(request.canon.scene) if s['id'] in selected_subjects]
            if {s['id'] for s in roster} != selected_subjects:
                raise ValueError('ASSET_REVISION_SUBJECT_SCOPE_MISMATCH')
            bases = {s['id']: next(a for a in parents if a.asset_type == AssetType.CHARACTER
                and a.content['specializedAsset']['subjectId'] == s['id']) for s in roster}
            original_context = packet.get('referenceAuthorContext') or dump_contract(request)
            original_request = AuthorRequest.model_validate(original_context)
            if (request.screenplay_context is not None
                    and request.screenplay_context != original_request.screenplay_context):
                raise ValueError('ASSET_REVISION_SCREENPLAY_BINDING_MISMATCH')
            context = {**(original_request.professional_context or {}), **(request.professional_context or {})}
            context.pop('assetSequence', None)
            context['assetPreparation'] = {'sceneOrdinal': next(i for i, s in enumerate(canon.scenes) if s.scene_id == packet['sceneId']),
                'narrativeRef': dump_contract(ref), 'revisionSourceRef': dump_contract(preparation_ref),
                'subjectCandidates': [{'selection': i, **s, 'inherited': dump_contract(bases[s['id']])} for i, s in enumerate(roster)],
                'assetCandidates': [{'selection': i, 'asset': dump_contract(a)} for i, a in enumerate(parents)]}
            scoped = request.model_copy(update={'scope': request.scope.model_copy(update={'shot_id': None}),
                'shot': None, 'professional_context': context,
                'screenplay_context': original_request.screenplay_context or request.screenplay_context})
            method = getattr(author, 'design_assets', None)
            if method is None:
                from drama_plugin.execution.transport import CapabilityAbsent
                raise CapabilityAbsent('SPECIALIZED_ASSET_AUTHOR_ABSENT')
            draft = SceneAssetDraft.model_validate(dump_contract(await method(scoped)))
            choices, claimed = [], set()
            for choice in draft.assets:
                ordinal = choice.reuse_selection
                if ordinal is None and choice.asset_type == 'CHARACTER' and choice.subject_selection is not None and choice.subject_selection < len(roster):
                    parent = bases[roster[choice.subject_selection]['id']]
                    ordinal = parents.index(parent)
                if ordinal is None or ordinal >= len(parents) or ordinal in claimed:
                    raise ValueError('ASSET_REVISION_EXACT_PARENT_SELECTION_REQUIRED')
                parent = parents[ordinal]
                if parent.asset_type != choice.asset_type:
                    raise ValueError('ASSET_REUSE_TYPE_MISMATCH')
                claimed.add(ordinal)
                stable = {k:v for k,v in parent.content['specializedAsset']['design'].items() if k not in {'proof', 'referenceLighting'}}
                if any(k not in {'proof', 'referenceLighting'} and (k not in stable or stable[k] != v) for k,v in choice.design.items()):
                    raise ValueError('ASSET_REVISION_STABLE_DESIGN_CHANGE')
                # Proof and reference light are re-authored candidates, never
                # inherited merely because an earlier FrameSpec selected them.
                design = {**stable, **{k:v for k,v in choice.design.items() if k in {'proof', 'referenceLighting'}}}
                choices.append(choice.model_copy(update={'reuse_selection': ordinal, 'design': design,
                    'reference_required': True, 'variant_reason': choice.variant_reason or draft.rationale}))
            if claimed != set(range(len(parents))):
                raise ValueError('ASSET_REVISION_EXACT_PARENT_SELECTION_REQUIRED')
            revised = self._project(ref, packet['sceneId'], roster, bases, parents,
                draft.model_copy(update={'assets': tuple(choices)}))
            revised['sceneScreenplayRef'] = packet.get('sceneScreenplayRef')
            revised['professionalBasisRefs'] = [dump_contract(preparation_ref), *[row['ref']
                for name in ('filmLook', 'locationCandidates') for row in context.get(name, [])]]
            revised['referenceAuthorContext'] = dump_contract(scoped)
            return self.objects.put('specialized-asset-preparation:' + sha256_canonical(
                [dump_contract(preparation_ref), list(asset_ids), revised]), revised)

    def _text_requirement(self, preparation_ref: SourcePin, requirement_key: str) -> tuple[dict[str, Any], dict[str, Any]]:
        packet = self.objects.read_ref(preparation_ref)
        if packet.get('schemaVersion') != 'specialized-asset-preparation-v1':
            raise ValueError('ASSET_PREPARATION_REQUIRED')
        selected = self.objects._path('asset-scene-design', [packet['narrativeRef']['fingerprint'], packet['sceneId']])
        if not selected.exists() or SourcePin.model_validate(self.objects._read(selected)) != preparation_ref:
            raise ValueError('ASSET_PREPARATION_NOT_SELECTED')
        narrative = self.objects.read_ref(SourcePin.model_validate(packet['narrativeRef']))
        if (narrative['workId'] != packet['workId']
                or packet['sceneId'] not in {row['sceneId'] for row in narrative['canon']['scenes']}):
            raise ValueError('ASSET_TEXT_HANDOFF_SCOPE_MISMATCH')
        rows = [row for row in packet['requirements'] if row['requirementKey'] == requirement_key]
        if len(rows) != 1:
            raise ValueError('ASSET_TEXT_REQUIREMENT_MISMATCH')
        item = rows[0]
        if item.get('reuseAssetId') or item.get('assetType') == 'CHARACTER' or item.get('referenceRequired') is not False:
            raise ValueError('ASSET_TEXT_HANDOFF_REQUIRES_UNREGISTERED_TEXT')
        design_ref = SourcePin.model_validate(item['designRef'])
        original = self.objects.read_ref(design_ref)
        material = {k: v for k, v in item.items() if k not in {'designRef', 'requirementKey'}}
        if original != material or design_ref.fingerprint != requirement_key:
            raise ValueError('ASSET_TEXT_DESIGN_IDENTITY_MISMATCH')
        return packet, item

    async def retain_text_handoff(self, preparation_ref: SourcePin, requirement_key: str, *,
                                  domains: tuple[SourceDomain, ...], rationale: str) -> SourcePin:
        """Keep an exact text original with Professional, without registering an image Asset.

        This transfers a pending storage duty, not artistic adoption or authorship.
        The selected preparation and every existing visual child remain unchanged.
        """
        if self.film_storage is None:
            raise ValueError('ASSET_TEXT_HANDOFF_REQUIRES_FILM_STORAGE')
        async with self._locks.setdefault('text-handoff:' + requirement_key, asyncio.Lock()):
            packet, item = self._text_requirement(preparation_ref, requirement_key)
            accepted = await self._available(packet['workId'], query=requirement_key,
                narrative_ref=SourcePin.model_validate(packet['narrativeRef']))
            if any(row.content['specializedAsset'].get('requirementKey') == requirement_key for row in accepted):
                raise ValueError('ASSET_TEXT_HANDOFF_ALREADY_REGISTERED')
            domains = tuple(SourceDomain(domain) for domain in domains)
            if not domains or len(set(domains)) != len(domains) or not rationale.strip():
                raise ValueError('ASSET_TEXT_HANDOFF_TARGET_REQUIRED')
            material = {'schemaVersion': 'specialized-asset-text-handoff-v1',
                'workId': packet['workId'], 'sceneId': packet['sceneId'],
                'preparationRef': dump_contract(preparation_ref), 'requirementKey': requirement_key,
                'designRef': item['designRef'], 'domains': sorted(domain.value for domain in domains),
                'rationale': rationale}
            path = self.objects._path('asset-text-handoff', [preparation_ref.fingerprint, requirement_key])
            ref = self.objects.put('specialized-asset-text-handoff:' + sha256_canonical(material), material)
            with self.objects._writer():
                if path.exists():
                    retained = SourcePin.model_validate(self.objects._read(path))
                    if self.objects.read_ref(retained) != material:
                        raise ValueError('ASSET_TEXT_HANDOFF_CONFLICT')
                    return retained
                self.objects._write(path, dump_contract(ref))
            return ref

    def _text_handoff(self, preparation_ref: SourcePin, requirement_key: str) -> dict[str, Any] | None:
        if self.film_storage is None:
            return None
        path = self.objects._path('asset-text-handoff', [preparation_ref.fingerprint, requirement_key])
        if not path.exists():
            return None
        packet, item = self._text_requirement(preparation_ref, requirement_key)
        ref = SourcePin.model_validate(self.objects._read(path))
        handoff = self.objects.read_ref(ref)
        if (handoff.get('schemaVersion') != 'specialized-asset-text-handoff-v1'
                or handoff.get('workId') != packet['workId'] or handoff.get('sceneId') != packet['sceneId']
                or handoff.get('preparationRef') != dump_contract(preparation_ref)
                or handoff.get('requirementKey') != requirement_key or handoff.get('designRef') != item['designRef']):
            raise ValueError('ASSET_TEXT_HANDOFF_IDENTITY_MISMATCH')
        domains = [SourceDomain(domain).value for domain in handoff.get('domains', [])]
        if not domains or len(set(domains)) != len(domains) or not handoff.get('rationale', '').strip():
            raise ValueError('ASSET_TEXT_HANDOFF_TARGET_REQUIRED')
        return {**item, 'handoffRef': dump_contract(ref), 'domains': domains,
            'handoffRationale': handoff['rationale']}

    async def _prepare(self, request: AuthorRequest, author: AssetAuthor, *,
                       narrative_ref: SourcePin | None = None) -> AuthorRequest:
        ref = narrative_ref or self.selected(request)
        if ref is None:
            return request
        canon = self._narrative(ref, request)
        scene_screenplays = self.objects.read_ref(ref).get('sceneScreenplayRefs', {})
        assert request.scope.scene_id is not None
        order = [s.scene_id for s in canon.scenes]
        target = order.index(request.scope.scene_id)
        available = await self._available(request.scope.work_id, query=ref.key, narrative_ref=ref)
        family = ref.fingerprint if self._fresh(ref) else None
        results = []
        for index, scene in enumerate(canon.scenes[:target + 1]):
            # A future variation cannot travel backwards merely because it exists.
            candidates = [a for a in available if a.content['specializedAsset']['establishedSceneId'] is None
                or a.content['specializedAsset']['establishedSceneId'] in order[:index + 1]]
            roster: list[dict[str, Any]] = subjects(scene.scene)
            bases = {s['id']: self._latest(candidates, self._character(request.scope.work_id, str(s['id']), family)) for s in roster}
            key = [ref.fingerprint, scene.scene_id]
            path = self.objects._path('asset-scene-design', key)
            if not path.exists():
                recovered = {}
                for asset in available:
                    value = asset.content['specializedAsset']
                    raw = value.get('scenePreparationOriginal')
                    if isinstance(raw, dict) and raw.get('sceneId') == scene.scene_id and raw.get('narrativeRef') == dump_contract(ref):
                        pin = SourcePin.model_validate(value['scenePreparationRef'])
                        if sha256_canonical(raw) != pin.fingerprint:
                            raise ValueError('ASSET_PREPARATION_RECOVERY_HASH_MISMATCH')
                        recovered[pin.fingerprint] = (pin, raw)
                if len(recovered) > 1:
                    raise ValueError('ASSET_PREPARATION_RECOVERY_AMBIGUOUS')
                if recovered:
                    pin, raw = next(iter(recovered.values()))
                    self.objects.put(pin.key, raw)
                    for item in raw['requirements']:
                        if item.get('reuseAssetId'):
                            continue
                        original = {k:v for k,v in item.items() if k not in {'designRef','requirementKey'}}
                        source = SourcePin.model_validate(item['designRef'])
                        if sha256_canonical(original) != source.fingerprint:
                            raise ValueError('ASSET_DESIGN_RECOVERY_HASH_MISMATCH')
                        self.objects.put(source.key, original)
                    with self.objects._writer():
                        self.objects._write(path, dump_contract(pin))
            if path.exists():
                prepared = SourcePin.model_validate(self.objects._read(path))
                packet = self.objects.read_ref(prepared)
            else:
                inherited_context = (request.professional_context or {}) if scene.scene_id == request.scope.scene_id else {
                    'filmLook': (request.professional_context or {}).get('filmLook', []), 'locationCandidates': []}
                handoff = (self.objects.read_ref(SourcePin.model_validate(scene_screenplays[scene.scene_id]))
                    if scene.scene_id in scene_screenplays else request.screenplay_context if scene.scene_id == request.scope.scene_id else None)
                if handoff:
                    from drama_plugin.creative_engine.screenplay import ScreenplayWorkshop
                    selected_context = ScreenplayWorkshop(self.objects).professional_context(handoff,
                        work_id=request.scope.work_id, scene_id=scene.scene_id)
                    inherited_context = {**inherited_context, **{k:v for k,v in selected_context.items() if v}}
                context: dict[str, Any] = {**inherited_context,
                    'assetPreparation': {'sceneOrdinal': index, 'narrativeRef': dump_contract(ref),
                        'subjectCandidates': [{'selection': i, **s, 'inherited': dump_contract(base) if (base := bases[s['id']]) else None}
                            for i, s in enumerate(roster)],
                        'assetCandidates': [{'selection': i, 'asset': dump_contract(a)} for i, a in enumerate(candidates)]}}
                scoped = request.model_copy(update={'scope': request.scope.model_copy(update={'scene_id': scene.scene_id, 'shot_id': None}),
                    'canon': CanonDraft(work=canon.work, script=canon.script, scene=scene.scene),
                    'shot': None, 'professional_context': context, 'screenplay_context': handoff, 'revision': None})
                method = getattr(author, 'design_assets', None)
                if method is None:
                    from drama_plugin.execution.transport import CapabilityAbsent
                    raise CapabilityAbsent('SPECIALIZED_ASSET_AUTHOR_ABSENT')
                draft = SceneAssetDraft.model_validate(dump_contract(await method(scoped)))
                packet = self._project(ref, scene.scene_id, roster, bases, candidates, draft)
                packet['sceneScreenplayRef'] = scene_screenplays.get(scene.scene_id)
                packet['professionalBasisRefs'] = [row['ref'] for name in ('filmLook', 'locationCandidates')
                    for row in context.get(name, [])]
                # The reference artist consumes this selected Scene, including
                # its inherited identities and actual Film Look observations.
                packet['referenceAuthorContext'] = dump_contract(scoped)
                prepared = self.objects.put('specialized-asset-preparation:' + sha256_canonical(key), packet)
                with self.objects._writer():
                    self.objects._write(path, dump_contract(prepared))
            bindings, text_designs = [], []
            for item in packet['requirements']:
                handoff = self._text_handoff(prepared, item['requirementKey'])
                if handoff is not None:
                    if any(a.content['specializedAsset'].get('requirementKey') == item['requirementKey'] for a in available):
                        raise ValueError('ASSET_TEXT_HANDOFF_ALREADY_REGISTERED')
                    text_designs.append(handoff)
                    continue
                existing = [a for a in available if a.content['specializedAsset'].get('requirementKey') == item['requirementKey']]
                if not existing:
                    exact = await self._available(request.scope.work_id, query=item['requirementKey'], narrative_ref=ref)
                    available = list({a.id: a for a in (*available, *exact)}.values())
                    existing = [a for a in available if a.content['specializedAsset'].get('requirementKey') == item['requirementKey']]
                if item.get('reuseAssetId'):
                    existing = [a for a in available if a.id == item['reuseAssetId']]
                if len(existing) != 1:
                    raise AssetPreparationPending(prepared)
                asset = existing[0]
                if item['referenceRequired'] and not asset.reference_media_ids:
                    raise AssetPreparationPending(prepared)
                resolved_media = []
                for media_id in asset.reference_media_ids:
                    media = await self.media.get_media(media_id)
                    self._media_identity(media, request.scope.work_id)
                    # Compact media identity, not nested Media.sourceRef (which
                    # has a different meaning from Professional sourceRef).
                    resolved_media.append({'mediaId': media.id, 'contentHash': media.content_hash,
                        'mediaType': media.media_type.value, 'width': media.content.get('width'),
                        'height': media.content.get('height'), 'durationMs': media.duration_ms,
                        'version': str(media.content.get('version', 1))})
                bindings.append({**dump_contract(asset), 'resolvedMedia': resolved_media})
            results.append({'sceneId': scene.scene_id, 'preparationRef': dump_contract(prepared),
                'assets': bindings, 'textDesigns': text_designs})
        context = {**(request.professional_context or {}),
            'assetSequence': {'narrativeRef': dump_contract(ref), 'preparedScenes': results,
                'currentAssets': results[-1]['assets'], 'currentTextDesigns': results[-1]['textDesigns']}}
        return request.model_copy(update={'professional_context': context})

    def _project(self, ref: SourcePin, scene_id: str, roster: list[dict[str, Any]],
                 bases: dict[str, Asset | None], candidates: list[Asset], draft: SceneAssetDraft) -> dict[str, Any]:
        work = self.objects.read_ref(ref)['workId']
        family = ref.fingerprint if self._fresh(ref) else None
        requirements = []
        claimed = set()
        for ordinal, choice in enumerate(draft.assets):
            from drama_plugin.professional_design.provenance import reject_model_metadata
            reject_model_metadata(choice.design)
            if choice.subject_selection is not None and choice.subject_selection >= len(roster):
                raise ValueError('ASSET_SUBJECT_SELECTION_OUT_OF_RANGE')
            subject = roster[choice.subject_selection]['id'] if choice.subject_selection is not None else None
            if choice.reuse_selection is not None and choice.reuse_selection >= len(candidates):
                raise ValueError('ASSET_REUSE_SELECTION_OUT_OF_RANGE')
            prior = candidates[choice.reuse_selection] if choice.reuse_selection is not None else None
            if prior is not None and not self._in_family(prior, ref):
                raise ValueError('ASSET_REUSE_FAMILY_MISMATCH')
            if choice.asset_type == 'CHARACTER':
                assert isinstance(subject, str)
                if subject in claimed:
                    raise ValueError('DUPLICATE_CHARACTER_ASSET_REQUIREMENT')
                claimed.add(subject)
                base = bases[subject]
                if prior and (prior.asset_type != AssetType.CHARACTER or prior.content['specializedAsset']['subjectId'] != subject):
                    raise ValueError('ASSET_CHARACTER_INHERITANCE_MISMATCH')
                prior = base or prior
                if prior is not None and not self._in_family(prior, ref):
                    raise ValueError('ASSET_REUSE_FAMILY_MISMATCH')
            if prior and prior.asset_type != choice.asset_type:
                raise ValueError('ASSET_REUSE_TYPE_MISMATCH')
            if choice.reference_role == 'SUPPLEMENT' and (prior is None or not choice.variant_reason):
                raise ValueError('SUPPLEMENT_REQUIRES_ACCEPTED_BASELINE')
            if prior and not choice.variant_reason:
                requirements.append(self._reuse(prior))
                continue
            if choice.variant_reason and prior is None:
                raise ValueError('ASSET_VARIANT_REQUIRES_ACCEPTED_PARENT')
            object_identity = [work, scene_id, choice.asset_type, ordinal]
            if family is not None:
                object_identity.append(family)
            identity = (prior.content['specializedAsset']['stableIdentity'] if prior else
                self._character(work, str(subject), family) if choice.asset_type == 'CHARACTER' else
                'specialized-asset:' + ('fresh:' if family is not None else '') + sha256_canonical(object_identity))
            material = {'assetType': choice.asset_type, 'name': choice.name, 'design': choice.design,
                'subjectId': subject, 'stableIdentity': identity,
                'revision': (prior.content['specializedAsset']['revision'] or 0) + 1 if prior else 1,
                'establishedSceneId': scene_id, 'inheritedFromAssetId': prior.id if prior else None,
                'identityRootAssetId': (prior.content['specializedAsset'].get('identityRootAssetId') or prior.id) if prior else None,
                'variantReason': choice.variant_reason, 'referenceRequired': choice.reference_required,
                'narrativeRef': dump_contract(ref)}
            if choice.reference_role == 'SUPPLEMENT':
                if prior is None or not choice.variant_reason:
                    raise ValueError('SUPPLEMENT_REQUIRES_ACCEPTED_BASELINE')
                material['referenceRole'] = 'SUPPLEMENT'
            if choice.reference_mode == 'image_to_image':
                if not choice.reference_required:
                    raise ValueError('IMAGE_TO_IMAGE_REQUIRES_REFERENCE_PRODUCTION')
                if any(i<0 or i>=len(candidates) for i in choice.reference_selections):
                    raise ValueError('ASSET_REFERENCE_SELECTION_OUT_OF_RANGE')
                inputs = [candidates[i] for i in choice.reference_selections] or ([prior] if prior else [])
                if not inputs or len({a.id for a in inputs}) != len(inputs):
                    raise ValueError('IMAGE_TO_IMAGE_REQUIRES_DISTINCT_ACCEPTED_INPUTS')
                if prior and choice.asset_type == 'CHARACTER' and prior.id not in {a.id for a in inputs}:
                    raise ValueError('IMAGE_TO_IMAGE_MUST_RETAIN_PARENT_IDENTITY')
                material.update(referenceMode='image_to_image', referenceAssetIds=[a.id for a in inputs])
            design_ref = self.objects.put('specialized-asset-design:' + identity, material)
            requirements.append({**material, 'designRef': dump_contract(design_ref),
                'requirementKey': design_ref.fingerprint})
        for s in roster:
            if s['id'] not in claimed:
                base = bases[s['id']]
                if base is None:
                    raise ValueError('FIRST_APPEARANCE_CHARACTER_DESIGN_REQUIRED')
                requirements.append(self._reuse(base))
        return {'schemaVersion': 'specialized-asset-preparation-v1', 'workId': work, 'sceneId': scene_id,
            'narrativeRef': dump_contract(ref), 'rationale': draft.rationale, 'requirements': requirements}

    @staticmethod
    def _reuse(asset: Asset) -> dict[str, Any]:
        value = asset.content['specializedAsset']
        return {**{k:value[k] for k in ('assetType','subjectId','stableIdentity','revision','requirementKey')}, 'reuseAssetId': asset.id,
            'referenceRequired': bool(asset.reference_media_ids)}

    async def accept(self, preparation_ref: SourcePin, requirement_key: str, *, adoption_ref: SourcePin,
                     reference_media_ids: tuple[str, ...] = (), reference_record: Any = None) -> Asset:
        """Consume an existing artistic adoption. No candidate auto-promotion or generation."""
        async with self._locks.setdefault('accept:' + requirement_key, asyncio.Lock()):
            return await self._accept(preparation_ref, requirement_key,
                adoption_ref=adoption_ref, reference_media_ids=reference_media_ids,
                reference_record=reference_record)

    async def _accept(self, preparation_ref: SourcePin, requirement_key: str, *, adoption_ref: SourcePin,
                      reference_media_ids: tuple[str, ...], reference_record: Any = None) -> Asset:
        packet = self.objects.read_ref(preparation_ref)
        if packet.get('schemaVersion') != 'specialized-asset-preparation-v1':
            raise ValueError('ASSET_PREPARATION_REQUIRED')
        selected = self.objects._path('asset-scene-design', [packet['narrativeRef']['fingerprint'], packet['sceneId']])
        review = self.objects.read_ref(adoption_ref)
        if reference_record is not None:
            if self.reference_production is None:
                raise ValueError('REFERENCE_EXACT_USER_DECISION_REQUIRED')
            self.reference_production.adopted_reference(reference_record, review, reference_media_ids)
            self.candidate_parent(preparation_ref)
            if (reference_record.preparation_ref != preparation_ref
                    or reference_record.requirement_key != requirement_key):
                raise ValueError('ASSET_DESIGN_ADOPTION_MISMATCH')
        elif not selected.exists() or SourcePin.model_validate(self.objects._read(selected)) != preparation_ref:
            raise ValueError('ASSET_PREPARATION_NOT_SELECTED')
        item = next(r for r in packet['requirements'] if r['requirementKey'] == requirement_key)
        narrative_ref = SourcePin.model_validate(packet['narrativeRef'])
        if item.get('reuseAssetId'):
            reused=await self.assets.get_asset(item['reuseAssetId'])
            if not self._in_family(reused, narrative_ref):
                raise ValueError('ASSET_REUSE_FAMILY_MISMATCH')
            storage=getattr(self,'film_storage',None)
            if storage is not None:storage.scene_asset_event(reused,packet['sceneId'],preparation_ref)
            return reused
        ref = SourcePin.model_validate(item['designRef'])
        original = self.objects.read_ref(ref)
        if (review.get('decision') not in {'APPROVE', 'ADOPT'} or review.get('workId') != packet['workId']
                or review.get('subjectFingerprint') != ref.fingerprint
                or review.get('referenceMediaIds', []) != list(reference_media_ids)):
            raise ValueError('ASSET_DESIGN_ADOPTION_MISMATCH')
        if reference_record is not None:
            self._reference_requirement_selection(preparation_ref, item)
        known = [a for a in await self._available(packet['workId'], query=requirement_key, narrative_ref=narrative_ref)
                 if a.content['specializedAsset'].get('requirementKey') == requirement_key]
        if known:
            exact = [a for a in known if tuple(a.reference_media_ids) == reference_media_ids]
            if len(exact) == 1:
                if reference_record is not None and exact[0].content['specializedAsset']['adoptionRef'] != dump_contract(adoption_ref):
                    raise ValueError('ASSET_REFERENCE_ALREADY_ADOPTED_BY_ANOTHER_DECISION')
                if reference_record is not None:
                    self._select_reference_requirement(preparation_ref, item)
                    if self.film_storage is not None:
                        self.film_storage.asset_event(exact[0])
                return exact[0]
            if len(known) != 1 or exact:
                raise ValueError('ASSET_ACCEPTED_VERSION_AMBIGUOUS')
            if reference_record is None:
                return known[0]
            if self.film_storage is None:
                raise ValueError('REFERENCE_REPLACEMENT_REQUIRES_CURRENT_ASSET_STORAGE')
        if original['referenceRequired'] and not reference_media_ids:
            raise ValueError('ASSET_ADOPTED_REFERENCE_REQUIRED')
        for mid in reference_media_ids:
            media = await self.media.get_media(mid)
            self._media_identity(media, packet['workId'])
        content = {'specializedAsset': {**original, 'state': 'ADOPTED', 'requirementKey': requirement_key,
            'designRef': dump_contract(ref), 'adoptionRef': dump_contract(adoption_ref),
            'designOriginal': original, 'adoptionOriginal': review,
            'scenePreparationRef': dump_contract(preparation_ref), 'scenePreparationOriginal': packet}}
        asset = await self.assets.create_asset(work_id=packet['workId'], asset_type=AssetType(original['assetType']),
            # Reusable assets belong to the Work. Their exact native debut Scene
            # is retained above; it is not an independently registered Service
            # Scene row and must not be invented as a Service scope identity.
            name=original['name'], content=content, reference_media_ids=list(reference_media_ids))
        fresh = await self.assets.get_asset(asset.id)
        if dump_contract(fresh) != dump_contract(asset) or not self._proof(fresh):
            raise ValueError('ASSET_REGISTRATION_READBACK_MISMATCH')
        if self.film_storage is not None:
            self.film_storage.asset_event(fresh)
        if reference_record is not None:
            self._select_reference_requirement(preparation_ref, item)
        return fresh

    async def set_reference_selection(self, selection: dict[str, Any], decision_ref: ArtifactReference) -> SourcePin:
        from .reference_roles import retain_selection
        async with self._locks.setdefault('reference-selection:' + selection['identity'], asyncio.Lock()):
            return await retain_selection(self, selection, decision_ref)

    @staticmethod
    def _media_identity(media: Media, work_id: str) -> None:
        import re
        if (media.work_id != work_id or not re.fullmatch('[a-f0-9]{64}', media.content_hash or '')
                or media.media_type not in {'IMAGE', 'VIDEO'}):
            raise ValueError('ASSET_REFERENCE_MEDIA_IDENTITY_MISMATCH')
        if (media.purpose in {'REVIEW_TEMPLATE', 'CANDIDATE', 'DEBUG_ONLY'}
                or media.content.get('usageMode') in {'TEMPLATE', 'CANDIDATE'}):
            raise ValueError('ASSET_REFERENCE_NOT_ADOPTED_VISUAL')


def register_asset_sequence_tools(registry: Any, sequence: SpecializedAssetSequence) -> None:
    from drama_plugin.tools.catalog import _domain_tool
    async def accept(preparation_ref: SourcePin, requirement_key: str, adoption_ref: SourcePin,
                     reference_media_ids: tuple[str, ...] = ()) -> Asset:
        return await sequence.accept(preparation_ref, requirement_key, adoption_ref=adoption_ref,
            reference_media_ids=reference_media_ids)
    async def read_preparation(reference: ArtifactReference) -> dict[str, Any]:
        if reference.owner != 'specialized-asset-preparation':
            raise ValueError('Wrong asset preparation owner')
        key, digest = reference.artifact_ref.rsplit(':', 1)
        ref = SourcePin(key=key, kind='DESIGN', fingerprint=digest)
        packet = sequence.objects.read_ref(ref)
        if packet.get('schemaVersion') != 'specialized-asset-preparation-v1':
            raise ValueError('Wrong asset preparation original')
        path = sequence.objects._path('asset-scene-design', [packet['narrativeRef']['fingerprint'], packet['sceneId']])
        if path.exists():
            selected = SourcePin.model_validate(sequence.objects._read(path))
            if (selected.key, selected.fingerprint) != (ref.key, ref.fingerprint):
                sequence.candidate_parent(ref)  # Exact review candidates are readable, never adopted here.
                ref = ref.model_copy(update={'kind': selected.kind})
            else:
                ref = selected
        return {'preparationRef': dump_contract(ref), **packet}
    registry.register(_domain_tool('specialized_assets.set_reference_selection',
        'Retain an explicitly approved baseline and supplemental reference selection without rewriting image originals.',
        sequence.set_reference_selection, SourcePin,
        required={'selection': dict[str, JsonValue], 'decision_ref': ArtifactReference}))
    registry.register(_domain_tool('specialized_assets.read_preparation',
        'Read the exact pending scene asset requirements for the existing Asset Resolution owner.',
        read_preparation, dict, required={'reference': ArtifactReference}))
    registry.register(_domain_tool('specialized_assets.accept',
        'Register one already adopted specialized asset; reuse exact accepted versions without regeneration.',
        accept, Asset, required={'preparation_ref': SourcePin, 'requirement_key': str, 'adoption_ref': SourcePin},
        optional={'reference_media_ids': tuple[str, ...]}, defaults={'reference_media_ids': ()}))
    registry.register(_domain_tool('specialized_assets.retain_text_handoff',
        'Retain an exact pending text design for Professional consumption without creating an image Asset.',
        sequence.retain_text_handoff, SourcePin,
        required={'preparation_ref': SourcePin, 'requirement_key': str,
            'domains': tuple[SourceDomain, ...], 'rationale': str}))
