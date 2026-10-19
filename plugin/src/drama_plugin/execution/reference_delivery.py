"""Late-bound delivery of an unchanged managed original, beneath the input seal.

Storage credentials and signing stay in the Media service. An expiring vendor
result URL is provenance only, never a durable reference or a trust renewal.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import json
import httpx
from dataclasses import dataclass
from collections.abc import Mapping

from drama_plugin.contracts.base import canonical_json, sha256_canonical
from drama_plugin.contracts.video import ProviderTask
from drama_plugin.execution.media import atomic_write
from drama_plugin.execution.transport import DefinitelyNotSubmitted
from drama_plugin.exceptions import RemoteServiceError
from drama_plugin.providers.video.base import SafeProviderError
from drama_plugin.providers.video.image_delivery import external_https


def credential_fingerprint(adapter) -> str:
    key = adapter.settings.api_key
    if not key:
        raise DefinitelyNotSubmitted('REFERENCE_ACCOUNT_UNVERIFIED')
    return sha256(key.get_secret_value().encode()).hexdigest()


def require_trusted_time(generated: datetime) -> None:
    now = datetime.now(timezone.utc)
    if not generated.tzinfo or generated > now or generated < datetime(2026, 3, 11, tzinfo=timezone.utc):
        raise DefinitelyNotSubmitted('REFERENCE_PROVENANCE_UNVERIFIED')
    if now >= generated + timedelta(days=30):
        raise DefinitelyNotSubmitted('REFERENCE_TRUST_EXPIRED')


@dataclass(frozen=True)
class OriginalImageIdentity:
    content_hash: str
    byte_count: int
    mime: str
    kind: str = 'IMAGE'


def adopted_original_image(adapter, media, asset, binding) -> OriginalImageIdentity:
    """Validate an adopted original portrait without inventing video provenance.

    Synchronous image creation has no video task ownership query. Its retained
    successful receipt and producing Host's same-credential attestation are
    required; these assert neither a numeric account ID nor a moderation grant.
    """
    def reject():
        raise DefinitelyNotSubmitted('REFERENCE_ADOPTED_IMAGE_PROOF_REQUIRED')
    try:
        value = asset.content['specializedAsset']
        design, adoption = value['designOriginal'], value['adoptionOriginal']
        proof = media.content['originalImageProvenance']
        receipt, attestation = proof['receipt'], proof['accountAttestation']
        selected = next(r for r in design['referenceMedia'] if r['mediaId'] == media.id)
        review = media.content['imageReview']
        if (asset.asset_type.value != 'CHARACTER' or value['state'] != 'ADOPTED'
                or sha256_canonical(design) != value['designRef']['fingerprint']
                or sha256_canonical(adoption) != value['adoptionRef']['fingerprint']
                or not all(value.get(k) == v for k, v in design.items())
                or adoption['decision'] not in {'APPROVE', 'ADOPT'}
                or adoption['subjectFingerprint'] != value['designRef']['fingerprint']
                or adoption['referenceMediaIds'] != asset.reference_media_ids
                or media.id not in asset.reference_media_ids
                or binding.media.review_ref != 'asset-adoption:' + asset.id + ':' + value['adoptionRef']['fingerprint']
                or (media.work_id, asset.work_id, adoption['workId'], design['workId']) != (binding.scope.work_id,) * 4
                or binding.origin_scope.work_id != binding.scope.work_id
                or (binding.source_scope is not None and (binding.source_scope.scene_id is not None
                    or binding.source_scope.shot_id is not None))
                or media.shot_id is not None or media.media_type.value != 'IMAGE'
                or media.mime_type not in {'image/png', 'image/jpeg'}
                or binding.subject_ids != (design['subjectId'],)
                or media.content['subjectId'] != design['subjectId']
                or selected['duty'] != 'IDENTITY_PORTRAIT'
                or selected['sha256'] != media.content_hash or binding.media.content_hash != media.content_hash
                or media.content['generationMode'] != 'TEXT_TO_IMAGE' or selected['generationMode'] != 'TEXT_TO_IMAGE'
                or not media.content['unalteredOriginal'] or not selected['unalteredOriginal']
                or media.content['sourceInputMediaIds'] or receipt['usage']['input_images'] != 0
                or review['output_hash'] != media.content_hash or not review['checks']
                or any(check != 'PASS' for check in review['checks'].values())
                or media.content['reviewStatus'] != 'PASS' or media.content['usageMode'] != 'ADOPTED'
                or receipt['status'] != 'COMPLETED' or receipt['diagnostics']['http_status'] != 200
                or receipt['provider'] != 'ark' or receipt['credential_source'] != 'DRAMA_VIDEO_SEEDANCE_API_KEY'
                or receipt['model'] not in {'doubao-seedream-5-0-pro-260628', 'doubao-seedream-5-0-260128'}
                or receipt['model'] != selected['modelId'] or receipt['model'] != media.content['modelId']
                or receipt['output_hash'] != media.content_hash or receipt['output_bytes'] != media.file_size
                or receipt['mime_type'] != media.mime_type or receipt['task_id'] != selected['taskId']
                or receipt['request_fingerprint'] != selected['sourceRequestFingerprint']
                or receipt['request_fingerprint'] != media.content['sourceCompiledRequestFingerprint']
                or attestation['evidence'] != 'HOST_OBSERVED_SYNCHRONOUS_CREATE_SAME_CONFIG'
                or attestation['receiptFingerprint'] != sha256_canonical(receipt)
                or proof['fingerprint'] != sha256_canonical({k:v for k,v in proof.items() if k != 'fingerprint'})):
            reject()
        if attestation['credentialFingerprint'] != credential_fingerprint(adapter):
            raise DefinitelyNotSubmitted('REFERENCE_ACCOUNT_UNVERIFIED')
        generated = datetime.fromtimestamp(receipt['created'], timezone.utc)
        if datetime.fromisoformat(selected['generatedAt']) != generated:
            reject()
        require_trusted_time(generated)
    except (KeyError, TypeError, StopIteration, ValueError):
        reject()
    return OriginalImageIdentity(media.content_hash, media.file_size, media.mime_type)


def native_asset_originals(ledger, objects, asset) -> dict:
    """Read exact Native owners instead of rebuilding proof in a Media index.

    The adopted Asset pins its original preparation/design/adoption. The adoption
    pins the immutable reference-production and user-decision records. Neither
    the current environment nor a caller-created account attestation is evidence
    of the credential used by the producing request.
    """
    from drama_plugin.contracts.base import dump_contract
    from drama_plugin.contracts.source_pin import SourcePin
    from drama_plugin.persistence.review import UserDecisionRecord
    from drama_plugin.professional_design.reference_production import ReferenceProductionRecord
    from drama_plugin.runtime.contracts import ArtifactReference

    def record(ref):
        if ref.owner != 'asset-reference-production':
            raise ValueError('REFERENCE_PRODUCTION_OWNER_REQUIRED')
        raw, scope, fingerprint = ledger.get_artifact(ref.owner, ref)
        value = ReferenceProductionRecord.model_validate(raw)
        if (value.artifact_reference() != ref or value.scope != scope
                or value.fingerprint != fingerprint
                or ledger.load_run(value.run_id).scope != value.scope):
            raise ValueError('REFERENCE_PRODUCTION_IDENTITY_MISMATCH')
        return value

    try:
        value = asset.content['specializedAsset']
        originals = {name: objects.read_ref(SourcePin.model_validate(value[key]))
            for name, key in (('designOriginal', 'designRef'), ('adoptionOriginal', 'adoptionRef'))}
        adoption = originals['adoptionOriginal']
        production = record(ArtifactReference.model_validate(adoption['referenceProductionRef']))
        if (value.get('scenePreparationRef') is not None
                and SourcePin.model_validate(value['scenePreparationRef']) != production.preparation_ref):
            raise ValueError('REFERENCE_PREPARATION_IDENTITY_MISMATCH')
        originals['preparationOriginal'] = objects.read_ref(production.preparation_ref)
        decision_ref = ArtifactReference.model_validate(adoption['userDecisionRef'])
        if decision_ref.owner != 'user-decision':
            raise ValueError('REFERENCE_ADOPTION_OWNER_REQUIRED')
        raw, scope, fingerprint = ledger.get_artifact(decision_ref.owner, decision_ref)
        decision = UserDecisionRecord.model_validate(raw)
        if (decision.artifact_reference() != decision_ref or decision.scope != scope
                or decision.fingerprint != fingerprint or not decision.source_ref):
            raise ValueError('REFERENCE_ADOPTION_IDENTITY_MISMATCH')
        before_adoption = record(decision.source_ref)
        result = {**originals, 'referenceRecord': dump_contract(production),
            'userDecisionOriginal': dump_contract(decision),
            'decisionSourceRecord': dump_contract(before_adoption)}
        confirmation = objects._path('historical-image-credential', _historical_credential_key(production))
        if confirmation.exists():
            result['historicalCredentialConfirmation'] = objects.read_ref(
                SourcePin.model_validate(objects._read(confirmation)))
        return result
    except (KeyError, TypeError, ValueError, OSError, AttributeError):
        raise DefinitelyNotSubmitted('REFERENCE_ADOPTED_IMAGE_PROOF_REQUIRED') from None


def native_character_originals(ledger, objects, asset) -> dict:
    """Compatibility name for the existing type-neutral Native owner reader."""
    return native_asset_originals(ledger, objects, asset)


def _historical_credential_key(record) -> list:
    from drama_plugin.contracts.base import dump_contract
    return [record.scope.work_id, dump_contract(record.artifact_reference()), sha256_canonical(record.receipt)]


def retain_historical_character_credential(objects, proof, *, credential_fingerprint: str,
        confirmation_source: str, confirmed_at: datetime, user_statement: str):
    """Retain a human's explicit historical-key confirmation as new evidence.

    This helper never edits a generating receipt or labels a later observation
    as contemporaneous. Its caller must have the actual human confirmation;
    merely finding one configured Key is insufficient.
    """
    from drama_plugin.contracts.base import dump_contract
    from drama_plugin.contracts.source_pin import SourcePin
    from drama_plugin.professional_design.reference_production import ReferenceProductionRecord
    record = ReferenceProductionRecord.model_validate(proof['referenceRecord'])
    receipt = record.receipt
    if (not receipt or receipt.get('credential_fingerprint') is not None
            or len(credential_fingerprint) != 64 or any(c not in '0123456789abcdef' for c in credential_fingerprint)
            or not confirmation_source.startswith('current-human-reply:') or len(confirmation_source) > 260
            or not user_statement.strip() or len(user_statement) > 1000
            or confirmed_at.tzinfo is None or confirmed_at > datetime.now(timezone.utc)
            or confirmed_at < datetime.fromtimestamp(receipt['created'],timezone.utc)):
        raise ValueError('EXPLICIT_HISTORICAL_CREDENTIAL_CONFIRMATION_REQUIRED')
    value = dict(schemaVersion='historical-image-credential-confirmation-v1',
        evidence='USER_CONFIRMED_HISTORICAL_UNCHANGED_CREDENTIAL', workId=record.scope.work_id,
        referenceProductionRef=dump_contract(record.artifact_reference()), receiptFingerprint=sha256_canonical(receipt),
        requestFingerprint=receipt['request_fingerprint'], outputHash=receipt['output_hash'],
        credentialFingerprint=credential_fingerprint, confirmationSource=confirmation_source,
        confirmedAt=confirmed_at.astimezone(timezone.utc).isoformat(), keyUnchangedSinceGeneration=True,
        userStatement=user_statement)
    key = _historical_credential_key(record)
    path = objects._path('historical-image-credential',key)

    def existing():
        if path.exists():
            existing_ref = SourcePin.model_validate(objects._read(path))
            original = objects.read_ref(existing_ref)
            if any(original.get(k) != value[k] for k in value if k != 'confirmedAt'):
                raise ValueError('HISTORICAL_CREDENTIAL_CONFIRMATION_CONFLICT')
            return existing_ref
        return None

    # put() takes the same owner guard. Avoid nested guards and unnecessary new
    # originals on ordinary replay, then check again before publishing the index.
    with objects._writer():
        if prior := existing():
            return prior
    ref = objects.put('historical-image-credential:'+sha256_canonical(key),value)
    with objects._writer():
        if prior := existing():
            return prior
        objects._write(path,dump_contract(ref))
    return ref


def _native_character_credential(adapter, production, proof) -> None:
    from drama_plugin.contracts.base import dump_contract
    receipt = production.receipt
    expected = credential_fingerprint(adapter)
    if 'credential_fingerprint' in receipt:
        if receipt['credential_fingerprint'] != expected:
            raise DefinitelyNotSubmitted('REFERENCE_ACCOUNT_UNVERIFIED')
        return
    confirmation = proof.get('historicalCredentialConfirmation',{})
    try:
        when = datetime.fromisoformat(confirmation['confirmedAt'])
        if (confirmation.get('schemaVersion') != 'historical-image-credential-confirmation-v1'
                or confirmation.get('evidence') != 'USER_CONFIRMED_HISTORICAL_UNCHANGED_CREDENTIAL'
                or confirmation.get('workId') != production.scope.work_id
                or confirmation.get('referenceProductionRef') != dump_contract(production.artifact_reference())
                or confirmation.get('receiptFingerprint') != sha256_canonical(receipt)
                or confirmation.get('requestFingerprint') != receipt['request_fingerprint']
                or confirmation.get('outputHash') != receipt['output_hash']
                or confirmation.get('credentialFingerprint') != expected
                or confirmation.get('keyUnchangedSinceGeneration') is not True
                or not confirmation.get('confirmationSource','').startswith('current-human-reply:')
                or not confirmation.get('userStatement','').strip() or when.tzinfo is None
                or when > datetime.now(timezone.utc) or when < datetime.fromtimestamp(receipt['created'],timezone.utc)):
            raise DefinitelyNotSubmitted('REFERENCE_ACCOUNT_UNVERIFIED')
    except (KeyError, TypeError, ValueError):
        raise DefinitelyNotSubmitted('REFERENCE_ACCOUNT_UNVERIFIED') from None


def _native_character_face_text(face: object) -> str:
    """Project only the selected original's observable craniofacial leaves.

    Hair remains its independent visual fact. The structured path is the exact
    four-leaf projection used by the retained artwork, not a free-form synopsis.
    Historical string originals keep their unchanged comparison.
    """
    if isinstance(face, str) and face.strip():
        return face
    if isinstance(face, dict):
        leaves = [face.get(key) for key in ('shape', 'eyes_brows', 'nose', 'mouth')]
        if all(isinstance(leaf, str) and leaf.strip() for leaf in leaves):
            return '；'.join(leaf for leaf in leaves if isinstance(leaf, str))
    raise ValueError('NATIVE_CHARACTER_FACE_PROJECTION_REQUIRED')


def _native_character_identity_review(checks: Mapping[str, str], *, reviewer: str = "") -> bool:
    """Read retained identity duties without renaming the actual review.

    The native Review contract permits professional check names. A reviewed
    single selected person with readable face/body is the explicit first-
    identity combination; an arbitrary PASS or fuzzy label never substitutes.
    All other checks remain subject to the caller's existing all-PASS test.
    """
    # An explicit human acceptance of the exact displayed candidate is also
    # identity authority. The caller still verifies the immutable ADOPTION
    # decision, exact review, source record, receipt and all checks below.
    human = (reviewer == 'HUMAN_APPROVAL_RECORDED_BY_HOST' and
        checks.get('USER_ACCEPTED_EXACT_CANDIDATE') == 'PASS' and
        checks.get('EXACT_BYTES_AND_FORMAL_READBACK') == 'PASS')
    return (human or checks.get('IDENTITY') == 'PASS' or
        all(checks.get(key) == 'PASS' for key in
            ('SINGLE_SELECTED_PERSON', 'FACE_AND_BODY_READABILITY')))


def native_adopted_character_image(adapter, media, asset, binding, proof) -> OriginalImageIdentity:
    """Validate an unchanged Native portrait against its real producing receipt.

    Compact Film Media need not repeat these originals. Missing historical
    credential evidence stays unverified; the bridge never manufactures it.
    """
    return _native_adopted_image(adapter, media, asset, binding, proof, asset_type='CHARACTER')


def native_adopted_asset_image(adapter, media, asset, binding, proof) -> OriginalImageIdentity:
    """Deliver a Native non-person original under its actual asset duty.

    Native records already retain the generating credential, immutable review
    and real adoption decision. No portrait or caller-created proof is needed.
    """
    if asset.asset_type.value not in {'LOCATION', 'COSTUME', 'PROP'}:
        raise DefinitelyNotSubmitted('REFERENCE_ADOPTED_IMAGE_PROOF_REQUIRED')
    return _native_adopted_image(adapter, media, asset, binding, proof, asset_type=asset.asset_type.value)


def _native_adopted_image(adapter, media, asset, binding, proof, *, asset_type: str) -> OriginalImageIdentity:
    from drama_plugin.contracts.base import dump_contract
    from drama_plugin.contracts.source_pin import SourcePin
    from drama_plugin.persistence.review import UserDecisionRecord
    from drama_plugin.professional_design.reference_production import ReferenceProductionRecord
    from drama_plugin.visual import production as still
    from drama_plugin.visual.execution import validate_result_identity

    def reject():
        raise DefinitelyNotSubmitted('REFERENCE_ADOPTED_IMAGE_PROOF_REQUIRED')

    try:
        value = asset.content['specializedAsset']
        production = ReferenceProductionRecord.model_validate(proof['referenceRecord'])
        prior = ReferenceProductionRecord.model_validate(proof['decisionSourceRecord'])
        decision = UserDecisionRecord.model_validate(proof['userDecisionOriginal'])
        preparation, design, adoption = (proof[k] for k in
            ('preparationOriginal', 'designOriginal', 'adoptionOriginal'))
        if not all((production.frame, production.stage, production.receipt,
                production.delivery, production.adoption_ref)):
            reject()
        frame, stage, receipt, delivery = production.frame, production.stage, production.receipt, production.delivery
        design_ref, adoption_ref = (SourcePin.model_validate(value[k]) for k in ('designRef', 'adoptionRef'))
        prep_ref = production.preparation_ref
        item = next(r for r in preparation['requirements'] if r['requirementKey'] == production.requirement_key)
        request = frame['request']
        attempt = next(a for a in stage['attempts'] if a['attempt_id'] == receipt['attempt_id'])
        review = still.current_review(attempt)
        actors = frame['spec']['actors']
        character = asset_type == 'CHARACTER'
        if character:
            appearance = design['design']
            if ('face' in appearance) == ('identity' in appearance):
                reject()
            identity_text = _native_character_face_text(appearance.get('face', appearance.get('identity')))
            ir_face = next(s['face']['text'] for s in frame['spec']['prompt_ir']['subjects']
                if s['id'] == design['subjectId'])
            frame_identity = (len(actors) == 1 and actors[0]['entity_key'] == design['subjectId']
                and actors[0]['identity'] == identity_text and ir_face == identity_text
                and actors[0]['visibility'] == 'FACE')
            duty, subject, semantics = 'CHARACTER', design['subjectId'], {'identity'}
        else:
            # Native still artwork may express an object entirely through its
            # sealed VisualPromptIR, without redundant low-level Prop fields.
            # Its design pin, exact request/receipt and original review remain
            # authoritative. Never invent a person or rewrite that request.
            frame_identity = not actors and not frame['spec']['prompt_ir']['subjects']
            if frame['spec']['props']:
                frame_identity = frame_identity and {p['entity_key'] for p in frame['spec']['props']} == {design['stableIdentity']}
            duty = {'LOCATION': 'LOCATION', 'COSTUME': 'COSTUME', 'PROP': 'CONTINUITY'}[asset_type]
            subject = design['stableIdentity']
            semantics = {'LOCATION': {'environment'}, 'COSTUME': {'costume'}, 'PROP': {'prop', 'continuity'}}[asset_type]
            if (binding.source_scope is None or getattr(binding, 'use_ref', None) is None
                    or getattr(binding, 'state_ref', None) is None
                    or binding.use_ref not in getattr(binding, 'authority_refs', ())):
                reject()
        if (asset.asset_type.value != asset_type or value['state'] != 'ADOPTED'
                or design != {k:v for k,v in item.items() if k not in {'designRef', 'requirementKey'}}
                or any(k in value and value[k] != v for k,v in design.items())
                or any(value.get(k) != design.get(k) for k in
                    ('assetType','name','design','subjectId','stableIdentity','revision','referenceRequired'))
                or design_ref.fingerprint != sha256_canonical(design)
                or item['designRef'] != dump_contract(design_ref) or item.get('reuseAssetId')
                or design.get('assetType') != asset_type
                or (not design.get('subjectId') if asset_type in {'CHARACTER', 'COSTUME'} else design.get('subjectId') is not None)
                or design.get('referenceRequired') is not True
                or prep_ref.fingerprint != sha256_canonical(preparation)
                or (value.get('scenePreparationRef') is not None
                    and SourcePin.model_validate(value['scenePreparationRef']) != prep_ref)
                or preparation['schemaVersion'] != 'specialized-asset-preparation-v1'
                or (preparation['workId'], preparation['sceneId']) !=
                    (production.scope.work_id, production.scope.scene_id)
                or design['establishedSceneId'] != production.scope.scene_id
                or adoption_ref.fingerprint != sha256_canonical(adoption)
                or adoption['decision'] not in {'APPROVE', 'ADOPT'}
                or adoption['subjectFingerprint'] != design_ref.fingerprint
                or adoption['referenceMediaIds'] != asset.reference_media_ids
                or adoption['referenceContentHash'] != media.content_hash
                or adoption['referenceProductionRef'] != dump_contract(production.artifact_reference())
                or adoption['userDecisionRef'] != dump_contract(production.adoption_ref)
                or adoption['reviewOriginal'] != review
                or decision.artifact_reference() != production.adoption_ref
                or decision.category.value != 'ADOPTION' or not decision.accepted
                or decision.scope != production.scope or decision.run_id != production.run_id
                or decision.source_ref != prior.artifact_reference()
                or any(getattr(prior,k) != getattr(production,k) for k in
                    ('run_id','scope','preparation_ref','requirement_key','frame','stage','receipt','delivery'))
                or production.asset_id not in (None, asset.id)
                or media.id not in asset.reference_media_ids
                or (media.work_id, asset.work_id, adoption['workId'], preparation['workId']) != (binding.scope.work_id,) * 4
                or binding.role != 'REFERENCE' or binding.subject_ids != ((design['subjectId'],) if character else ())
                or binding.authorization_scope != 'ADOPTED_PRODUCTION_INPUT'
                or binding.origin_scope.work_id != binding.scope.work_id
                or (binding.source_scope is not None and
                    (binding.source_scope.scene_id != design['establishedSceneId'] or binding.source_scope.shot_id is not None))
                or not binding.duties or any(d.role != duty or d.subject != subject for d in binding.duties)
                or (not semantics <= set(binding.media.semantics) if character else set(binding.media.semantics) != semantics)
                or binding.media.review_ref != 'asset-adoption:' + asset.id + ':' + adoption_ref.fingerprint
                or binding.media.content_hash != media.content_hash or binding.media.media_id != media.id
                or media.shot_id is not None or media.media_type.value != 'IMAGE' or media.purpose != asset_type + '_REFERENCE'
                or media.mime_type not in {'image/png','image/jpeg'}
                or delivery.get('persistenceStatus') != 'VERIFIED' or delivery['mediaId'] != media.id
                or delivery['contentHash'] != media.content_hash or delivery['sourceRef'] != media.source_ref
                or media.source_ref != 'asset-reference:' + attempt['attempt_id']
                or not frame_identity
                or frame['spec'].get('references') or frame['spec'].get('edit_source')
                or frame['spec'].get('image_mode','text_to_image') != 'text_to_image'
                or request.get('tool') != 'image.create' or request['body'].get('image')
                or frame['spec']['shot_id'] != 'asset-reference:' + production.requirement_key
                or frame['spec']['shot_fingerprint'] != design_ref.fingerprint
                or receipt['status'] != 'COMPLETED' or receipt['diagnostics']['http_status'] != 200
                or receipt['provider'] != 'ark' or receipt['credential_source'] != 'DRAMA_VIDEO_SEEDANCE_API_KEY'
                or receipt['model'] != request['body']['model'] or receipt['model'] != frame['template']['model']
                or receipt['model'] not in {'doubao-seedream-5-0-pro-260628','doubao-seedream-5-0-260128'}
                or receipt['work_id'] != media.work_id or receipt['request_fingerprint'] != sha256_canonical(request)
                or attempt['request'] != request or attempt['status'] != 'COMPLETED'
                or receipt['output_hash'] != media.content_hash or attempt['output_hash'] != media.content_hash
                or receipt['output_bytes'] != media.file_size or receipt['mime_type'] != media.mime_type
                or attempt['job_id'] != receipt['task_id'] or receipt['usage'].get('input_images',0) != 0
                or not still.usable(attempt) or review['output_hash'] != media.content_hash
                or review['attempt_id'] != attempt['attempt_id']
                or (not _native_character_identity_review(review['checks'], reviewer=review.get('reviewer', '')) if character else not review['checks'])
                or any(check != 'PASS' for check in review['checks'].values())):
            reject()
        validate_result_identity(attempt, receipt['correlation'], receipt['task_id'])
        target = tuple(frame['template']['output_size'])
        # Width/height are optional on VideoReference. The retained byte-pinned
        # production probe is authoritative when a compact binding omits them;
        # a supplied conflicting dimension must still fail before delivery.
        if (target not in {(s.get('width'),s.get('height')) for s in delivery['technical']['streams']}
                or binding.media.width is not None and binding.media.width != target[0]
                or binding.media.height is not None and binding.media.height != target[1]):
            reject()
        if not character and not receipt.get('credential_fingerprint'):
            raise DefinitelyNotSubmitted('REFERENCE_ACCOUNT_UNVERIFIED')
        _native_character_credential(adapter, production, proof)
        require_trusted_time(datetime.fromtimestamp(receipt['created'],timezone.utc))
    except (KeyError, TypeError, StopIteration, ValueError, AttributeError):
        reject()
    return OriginalImageIdentity(media.content_hash, media.file_size, media.mime_type)


def adopted_prop_original_image(adapter, media, asset, binding, proof) -> OriginalImageIdentity:
    """Deliver a reviewed native Prop original, with no portrait impersonation.

    Film V2 returns compact Asset/Media indexes. The caller reads these exact
    retained originals through their existing owners; it must not reconstruct
    provenance from the index or infer adoption from an image review alone.
    """
    from drama_plugin.contracts.base import dump_contract, sha256_canonical
    from drama_plugin.contracts.source_pin import SourcePin
    from drama_plugin.professional_design.reference_production import ReferenceProductionRecord
    from drama_plugin.visual import production as still
    from drama_plugin.visual.execution import validate_result_identity

    def reject():
        raise DefinitelyNotSubmitted('REFERENCE_ADOPTED_PROP_PROOF_REQUIRED')

    try:
        if proof['fingerprint'] != sha256_canonical({k:v for k,v in proof.items() if k != 'fingerprint'}):
            reject()
        value = asset.content['specializedAsset']
        record = ReferenceProductionRecord.model_validate(proof['referenceRecord'])
        preparation, design, adoption = (proof[k] for k in
            ('preparationOriginal', 'designOriginal', 'adoptionOriginal'))
        attestation = proof['accountAttestation']
        if not record.frame or not record.stage or not record.receipt or not record.delivery or not record.adoption_ref:
            reject()
        frame, stage, receipt, delivery = record.frame, record.stage, record.receipt, record.delivery
        item = next(r for r in preparation['requirements'] if r['requirementKey'] == record.requirement_key)
        design_ref, adoption_ref = (SourcePin.model_validate(value[k]) for k in ('designRef', 'adoptionRef'))
        request = frame['request']
        attempt = next(a for a in stage['attempts'] if a['attempt_id'] == receipt['attempt_id'])
        review = still.current_review(attempt)
        expected_design = {k:v for k,v in item.items() if k not in {'designRef','requirementKey'}}
        checks = review['checks']
        if (asset.asset_type.value != 'PROP' or value['state'] != 'ADOPTED'
                or design != expected_design or design_ref.fingerprint != sha256_canonical(design)
                or item['designRef'] != dump_contract(design_ref) or item.get('reuseAssetId')
                or design.get('assetType') != 'PROP' or design.get('subjectId') is not None
                or design.get('referenceRequired') is not True
                or value['stableIdentity'] != design['stableIdentity'] or value['revision'] != design['revision']
                or value['design'] != design['design']
                or record.preparation_ref.fingerprint != sha256_canonical(preparation)
                or preparation['schemaVersion'] != 'specialized-asset-preparation-v1'
                or preparation['workId'] != record.scope.work_id or preparation['sceneId'] != record.scope.scene_id
                or item['requirementKey'] != design_ref.fingerprint
                or adoption_ref.fingerprint != sha256_canonical(adoption)
                or adoption['decision'] not in {'APPROVE','ADOPT'}
                or adoption['subjectFingerprint'] != design_ref.fingerprint
                or adoption['referenceMediaIds'] != asset.reference_media_ids
                or adoption.get('referenceContentHash') != media.content_hash
                or adoption['referenceProductionRef'] != dump_contract(record.artifact_reference())
                or adoption['userDecisionRef'] != dump_contract(record.adoption_ref)
                or adoption['reviewOriginal'] != review
                or record.asset_id not in (None, asset.id)
                or media.id not in asset.reference_media_ids
                or (media.work_id, asset.work_id, adoption['workId'], preparation['workId']) != (binding.scope.work_id,) * 4
                or binding.role != 'REFERENCE' or binding.subject_ids
                or binding.authorization_scope != 'ADOPTED_PRODUCTION_INPUT'
                or binding.origin_scope.work_id != binding.scope.work_id
                or not binding.duties or any(d.role != 'CONTINUITY' or d.subject != design['stableIdentity'] for d in binding.duties)
                or not {'prop','continuity'} <= set(binding.media.semantics)
                or binding.media.review_ref != 'prop-asset-adoption:' + asset.id + ':' + sha256_canonical(proof)
                or binding.media.content_hash != media.content_hash or binding.media.media_id != media.id
                or media.shot_id is not None or media.media_type.value != 'IMAGE' or media.purpose != 'PROP_REFERENCE'
                or media.mime_type not in {'image/png','image/jpeg'}
                or delivery.get('persistenceStatus') != 'VERIFIED' or delivery['mediaId'] != media.id
                or delivery['contentHash'] != media.content_hash or delivery['sourceRef'] != media.source_ref
                or media.source_ref != 'asset-reference:' + attempt['attempt_id']
                or frame['spec']['actors'] or frame['spec'].get('references') or frame['spec'].get('edit_source')
                or {p['entity_key'] for p in frame['spec']['props']} != {design['stableIdentity']}
                or frame['spec'].get('image_mode','text_to_image') != 'text_to_image'
                or request.get('tool') != 'image.create' or request['body'].get('image')
                or frame['spec']['shot_id'] != 'asset-reference:' + record.requirement_key
                or frame['spec']['shot_fingerprint'] != design_ref.fingerprint
                or receipt['status'] != 'COMPLETED' or receipt['diagnostics']['http_status'] != 200
                or receipt['provider'] != 'ark' or receipt['credential_source'] != 'DRAMA_VIDEO_SEEDANCE_API_KEY'
                or receipt['model'] != request['body']['model'] or receipt['model'] != frame['template']['model']
                or receipt['model'] not in {'doubao-seedream-5-0-pro-260628','doubao-seedream-5-0-260128',
                    'doubao-seedream-5-0-flash-260915'}
                or receipt['work_id'] != media.work_id or receipt['request_fingerprint'] != sha256_canonical(request)
                or attempt['request'] != request or attempt['status'] != 'COMPLETED'
                or receipt['output_hash'] != media.content_hash or attempt['output_hash'] != media.content_hash
                or receipt['output_bytes'] != media.file_size or receipt['mime_type'] != media.mime_type
                or attempt['job_id'] != receipt['task_id'] or receipt['usage'].get('input_images', 0) != 0
                or not still.usable(attempt) or review['output_hash'] != media.content_hash
                or review['attempt_id'] != attempt['attempt_id']
                or not {'NO_PEOPLE','PROP_STRUCTURE','PROP_SCALE','PROP_MATERIAL'} <= set(checks)
                or any(check != 'PASS' for check in checks.values())
                or attestation['evidence'] != 'HOST_OBSERVED_SYNCHRONOUS_CREATE_SAME_CONFIG'
                or attestation['referenceProductionRef'] != dump_contract(record.artifact_reference())
                or attestation['receiptFingerprint'] != sha256_canonical(receipt)):
            reject()
        validate_result_identity(attempt, receipt['correlation'], receipt['task_id'])
        if attestation['credentialFingerprint'] != credential_fingerprint(adapter):
            raise DefinitelyNotSubmitted('REFERENCE_ACCOUNT_UNVERIFIED')
        sizes = {(s.get('width'),s.get('height')) for s in delivery['technical']['streams']}
        target = tuple(frame['template']['output_size'])
        if target not in sizes or (binding.media.width,binding.media.height) != target:
            reject()
        require_trusted_time(datetime.fromtimestamp(receipt['created'],timezone.utc))
    except (KeyError, TypeError, StopIteration, ValueError, AttributeError):
        reject()
    return OriginalImageIdentity(media.content_hash, media.file_size, media.mime_type)


def reviewed_original_frame(adapter, media, binding) -> OriginalImageIdentity:
    """Deliver a current-shot opening, independently of character asset adoption.

    Exact source/edit mode and the current image review establish technical
    delivery. They do not grant portrait trust. Edited images without human-style
    faces are ordinary inputs; edited portraits require a separate official
    trusted-asset route, never a fabricated text-to-image provenance.
    """
    def reject():
        raise DefinitelyNotSubmitted('FIRST_FRAME_REVIEW_OR_PROVENANCE_REQUIRED')
    try:
        c = media.content
        review, proof = c['imageReview'], c['originalImageProvenance']
        receipt, attestation = proof['receipt'], proof['accountAttestation']
        inputs = c['sourceInputMediaIds']
        mode = c['generationMode']
        if (binding.role != 'FIRST_FRAME' or binding.endpoint_frame_ref is not None
                or binding.origin_scope != binding.scope
                or media.media_type.value != 'IMAGE' or media.purpose != 'START_FRAME'
                or media.mime_type not in {'image/png', 'image/jpeg'}
                or media.work_id != binding.scope.work_id
                or c['targetNativeSceneId'] != binding.scope.scene_id
                or c['targetNativeShotId'] != binding.scope.shot_id
                or binding.media.content_hash != media.content_hash
                or review['scope'] != binding.scope.model_dump(mode='json')
                or review['output_hash'] != media.content_hash
                or binding.media.review_ref != 'image-review:' + sha256_canonical(review)
                or review['state_ref'] != binding.state_ref.model_dump(mode='json')
                or review['authority_refs'] != [r.model_dump(mode='json') for r in binding.authority_refs]
                or not {'CURRENT_SCENE','OPENING_STATE','FACE_CLASSIFICATION'} <= set(review['checks'])
                or any(v != 'PASS' for v in review['checks'].values())
                or c['reviewStatus'] != 'PASS' or c['usageMode'] != 'ADOPTED'
                or not c['unalteredOriginal']
                or mode not in {'TEXT_TO_IMAGE','IMAGE_TO_IMAGE'}
                or not isinstance(inputs,list) or len(inputs) != len(set(inputs))
                or (mode == 'TEXT_TO_IMAGE') != (len(inputs) == 0)
                or receipt['usage']['input_images'] != len(inputs)
                or receipt['status'] != 'COMPLETED' or receipt['diagnostics']['http_status'] != 200
                or receipt['provider'] != 'ark' or receipt['credential_source'] != 'DRAMA_VIDEO_SEEDANCE_API_KEY'
                or receipt['model'] != c['modelId']
                or receipt['output_hash'] != media.content_hash or receipt['output_bytes'] != media.file_size
                or receipt['mime_type'] != media.mime_type
                or receipt['request_fingerprint'] != c['sourceCompiledRequestFingerprint']
                or attestation['evidence'] != 'HOST_OBSERVED_SYNCHRONOUS_CREATE_SAME_CONFIG'
                or attestation['receiptFingerprint'] != sha256_canonical(receipt)
                or proof['fingerprint'] != sha256_canonical({k:v for k,v in proof.items() if k != 'fingerprint'})):
            reject()
        if attestation['credentialFingerprint'] != credential_fingerprint(adapter):
            raise DefinitelyNotSubmitted('REFERENCE_ACCOUNT_UNVERIFIED')
        generated = datetime.fromtimestamp(receipt['created'], timezone.utc)
        if generated > datetime.now(timezone.utc):
            reject()
        if c['faceContent'] == 'HUMAN_STYLE':
            if mode != 'TEXT_TO_IMAGE' or receipt['model'] not in {
                    'doubao-seedream-5-0-pro-260628', 'doubao-seedream-5-0-260128'}:
                raise DefinitelyNotSubmitted('SEEDANCE_EDITED_PORTRAIT_TRUST_UNVERIFIED')
            require_trusted_time(generated)
        elif c['faceContent'] != 'NONE':
            reject()
    except (KeyError, TypeError, ValueError, AttributeError):
        reject()
    return OriginalImageIdentity(media.content_hash, media.file_size, media.mime_type)


async def verify_origin(adapter, root: Path, origin, receipt, attempt, content_hash: str) -> None:
    """Authenticate historical ownership once; retain immutable task evidence.

    No numeric account identity is inferred. A changed credential requires the
    exact official task to be accessible again; Provider moderation is final.
    """
    account = credential_fingerprint(adapter)
    if receipt.source_account_fingerprint == account and receipt.source_generated_at is not None:
        require_trusted_time(receipt.source_generated_at)
        return
    identity = {'operationRef': origin.artifact_reference().model_dump(mode='json', by_alias=True),
                'provider': receipt.provider, 'model': origin.model, 'taskId': receipt.remote_identity,
                'contentHash': content_hash, 'credentialFingerprint': account}
    path = root / (sha256_canonical(identity) + '.reference-origin.json')
    if path.exists():
        proof = json.loads(path.read_bytes())
        if proof.get('identity') != identity or proof.get('status') != 'SUCCEEDED':
            raise DefinitelyNotSubmitted('REFERENCE_PROVENANCE_CONFLICT')
        generated = datetime.fromisoformat(proof['generatedAt'])
    else:
        try:
            task = await adapter.get_task(ProviderTask(provider=receipt.provider, model=origin.model,
                provider_task_id=receipt.remote_identity, client_request_id=attempt.client_identity,
                request_fingerprint=attempt.request_fingerprint, status='RUNNING'))
        except (SafeProviderError, httpx.HTTPError):
            raise DefinitelyNotSubmitted('REFERENCE_ACCOUNT_UNVERIFIED') from None
        if task.status != 'SUCCEEDED' or task.provider_task_id != receipt.remote_identity:
            raise DefinitelyNotSubmitted('REFERENCE_ACCOUNT_UNVERIFIED')
        generated = task.completed_at or task.created_at
        if generated is None:
            raise DefinitelyNotSubmitted('REFERENCE_PROVENANCE_UNVERIFIED')
        require_trusted_time(generated)
        # Do not change the old terminal receipt or persist its expired locator again.
        atomic_write(path, canonical_json({'identity': identity, 'status': 'SUCCEEDED',
            'generatedAt': generated.isoformat(), 'evidence': 'AUTHENTICATED_EXACT_OFFICIAL_TASK'}).encode())
    require_trusted_time(generated)


async def managed_original_url(provider, client: httpx.AsyncClient, identity, scope, *, media_id: str) -> str:
    if provider is None:
        raise DefinitelyNotSubmitted('REFERENCE_PUBLIC_DELIVERY_UNCONFIGURED')
    media = await provider.get_media(media_id)
    if (media.id, media.work_id, media.shot_id, media.content_hash, media.file_size, media.mime_type,
            media.media_type.value) != (media_id, scope.work_id, scope.shot_id, identity.content_hash,
            identity.byte_count, identity.mime, identity.kind):
        raise DefinitelyNotSubmitted('REFERENCE_MANAGED_ORIGINAL_MISMATCH')
    # Called for every actual dispatch; the URL is never cached into a package.
    try:
        delivery = await provider.resolve_media(media_id, provider_delivery=True)
    except RemoteServiceError as exc:
        code = ('REFERENCE_PUBLIC_DELIVERY_UNCONFIGURED' if exc.error_code == 'UNRESOLVABLE_MEDIA'
                else 'REFERENCE_DELIVERY_UNAVAILABLE')
        raise DefinitelyNotSubmitted(code) from None
    now = datetime.now(timezone.utc)
    if (delivery.media_id != media_id or delivery.size_bytes != identity.byte_count
            or delivery.mime_type != identity.mime or not delivery.expires_at.tzinfo
            or delivery.expires_at <= now + timedelta(minutes=2)):
        raise DefinitelyNotSubmitted('REFERENCE_DELIVERY_INVALID_OR_EXPIRED')
    url = urlsplit(delivery.url)
    # Reuse the configured store's public protocol. Generation API auth stays
    # on HTTPS; a bare object GET carries no API or storage credentials.
    if url.scheme not in ('http','https') or not external_https(urlunsplit(url._replace(scheme='https'))):
        raise DefinitelyNotSubmitted('REFERENCE_PUBLIC_DELIVERY_UNCONFIGURED')
    digest, size = sha256(), 0
    try:
        # Bare request: neither Provider API auth nor Media service auth reaches storage.
        request = httpx.Request('GET', delivery.url)
        response = await client.send(request, auth=None, follow_redirects=False, stream=True)
        try:
            response.raise_for_status()
            if response.headers.get('content-type', '').split(';', 1)[0] != identity.mime:
                raise DefinitelyNotSubmitted('REFERENCE_ORIGINAL_MIME_MISMATCH')
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > min(identity.byte_count, 256 * 1024 * 1024):
                    raise DefinitelyNotSubmitted('REFERENCE_ORIGINAL_BYTES_MISMATCH')
                digest.update(chunk)
        finally:
            await response.aclose()
    except httpx.HTTPError:
        raise DefinitelyNotSubmitted('REFERENCE_DELIVERY_UNREACHABLE') from None
    if size != identity.byte_count or digest.hexdigest() != identity.content_hash:
        raise DefinitelyNotSubmitted('REFERENCE_ORIGINAL_BYTES_MISMATCH')
    if delivery.expires_at <= datetime.now(timezone.utc) + timedelta(minutes=2):
        raise DefinitelyNotSubmitted('REFERENCE_DELIVERY_INVALID_OR_EXPIRED')
    return delivery.url
