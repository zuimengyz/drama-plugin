"""Formal design-only entry and movie-level immutable runtime authority."""
from pathlib import Path
from typing import Any, Mapping
from ..config import DramaPluginConfig, load_config
from ..contracts.base import dump_contract, sha256_canonical
from ..contracts.source_pin import SourcePin
from ..contracts.specialized_asset import MovieVisualMedium, GlobalVisualStyle, SpecializedAssetBible
from ..specialized_asset import compile_asset, validate_assets, provider_projection
from .director_artifacts import DirectorArtifactStore


class SpecializedAssetHost:
    def __init__(self, config: DramaPluginConfig):
        if not config.visual_authority_root or not Path(config.visual_authority_root).is_absolute():
            raise ValueError('VISUAL_AUTHORITY_ROOT_REQUIRED: configure one absolute movie authority store')
        self.config = config
        self.store = DirectorArtifactStore(config.visual_authority_root)

    def bind_movie(self, work_id: str) -> SourcePin:
        """Only runtime configuration can create this write-once per-Work record."""
        path = self.store._path('movie-medium', work_id)
        with self.store._writer():
            if path.exists():
                value = MovieVisualMedium.model_validate(self.store._read(path))
                if value.work_id != work_id:
                    raise ValueError('MOVIE_VISUAL_AUTHORITY_MISMATCH')
            else:
                if self.config.visual_medium is None:
                    raise ValueError('VISUAL_MEDIUM_CONFIGURATION_REQUIRED')
                value = MovieVisualMedium(work_id=work_id,
                    medium='CG' if self.config.visual_medium == 'cg' else 'LIVE_ACTION',
                    configuration_source=self.config.visual_medium_source)
                self.store._write(path, dump_contract(value))
        return self.store.put('runtime-medium:' + work_id, dump_contract(value))

    def movie(self, work_id: str) -> SourcePin:
        value = MovieVisualMedium.model_validate(self.store._read(self.store._path('movie-medium', work_id)))
        if value.work_id != work_id:
            raise ValueError('MOVIE_VISUAL_AUTHORITY_MISMATCH')
        return SourcePin(key='runtime-medium:' + work_id, kind='DIRECTION', fingerprint=sha256_canonical(value))

    def save_style(self, style: GlobalVisualStyle) -> SourcePin:
        style = GlobalVisualStyle.model_validate(dump_contract(style))
        if style.runtime_ref != self.movie(style.work_id):
            raise ValueError('MOVIE_VISUAL_AUTHORITY_MISMATCH')
        medium = MovieVisualMedium.model_validate(self.store.read_ref(style.runtime_ref))
        if ((medium.medium == 'CG') != (style.render_stylization is not None)
                or medium.medium == 'LIVE_ACTION' and style.realism != 'NATURALISTIC'):
            raise ValueError('RENDER_STYLIZATION_MEDIUM_MISMATCH')
        return self.store.put('global-style:' + style.work_id, dump_contract(style))

    def _inputs(self, bible: SpecializedAssetBible, current: Mapping[str, str]) -> tuple[dict[str, Any], dict[str, str]]:
        if bible.runtime_ref != self.movie(bible.work_id):
            raise ValueError('MOVIE_VISUAL_AUTHORITY_MISMATCH')
        refs = [bible.runtime_ref, bible.style_ref]
        if bible.approval_ref:
            refs.append(bible.approval_ref)
        for asset in bible.assets:
            refs.extend((asset.dramaturgy.bible_ref, asset.director.bible_ref, asset.world.bible_ref))
        from .professional import ProfessionalDepartmentHost
        originals = ProfessionalDepartmentHost(self.store.root)._artifacts(tuple(refs))
        return originals, {**current, bible.runtime_ref.key: bible.runtime_ref.fingerprint}

    def submit(self, bible: SpecializedAssetBible, *, current: Mapping[str, str]) -> SourcePin:
        originals, resolved = self._inputs(bible, current)
        validate_assets(bible, originals, resolved)
        return self.store.put('specialized-assets:' + bible.work_id, dump_contract(bible))

    def compile(self, ref: SourcePin, asset_id: str, *, current: Mapping[str, str],
                casting_mode: str = 'DESIGN_NEUTRAL') -> dict[str, Any]:
        if current.get(ref.key) != ref.fingerprint:
            raise ValueError('STALE_SPECIALIZED_ASSET')
        bible = SpecializedAssetBible.model_validate(self.store.read_ref(ref))
        originals, resolved = self._inputs(bible, current)
        receipt = compile_asset(bible, asset_id, originals, resolved, casting_mode=casting_mode)
        projection = provider_projection(receipt, originals, resolved)
        retained = self.store.put('asset-compilation:' + bible.work_id + ':' + asset_id, receipt)
        return {'compilationRef': dump_contract(retained), 'compilation': receipt, 'projection': projection}

    def department_records(self, ref: SourcePin, asset_ids: tuple[str, ...], department: str,
                           *, current: Mapping[str, str]) -> tuple[Any, ...]:
        """Project into existing department consumers without a second design author.

        The caller retains the usual Bible scope/dependencies and review procedure;
        professional.validate_bible replays these exact values on every consumption.
        """
        from ..contracts.professional import CreativeRecord
        from ..specialized_asset import department_values
        if current.get(ref.key) != ref.fingerprint:
            raise ValueError('STALE_SPECIALIZED_ASSET')
        bible = SpecializedAssetBible.model_validate(self.store.read_ref(ref))
        originals, resolved = self._inputs(bible, current)
        validate_assets(bible, originals, resolved)
        return tuple(CreativeRecord(id=identity, scope_refs=(bible.work_id,),
            values=department_values(bible, identity, department, originals, resolved),
            provenance='SPECIALIZED_ASSET_PROJECTION', source_refs=(ref,)) for identity in asset_ids)


def require_production_visual_authority(work: Any) -> list[dict[str, Any]]:
    """Called before paid reservation/submission, including legacy entry points.

    Compilation proves design lineage only. Existing creative/spend authorization
    and provider capability gates remain necessary and are never granted here.
    """
    host = SpecializedAssetHost(load_config())
    runtime = SourcePin.model_validate(work.content.get('movieVisualMediumRef', {}))
    if runtime != host.movie(work.id):
        raise ValueError('MOVIE_VISUAL_AUTHORITY_MISMATCH')
    refs = work.content.get('specializedAssetCompilationRefs', [])
    current = work.content.get('visualSourceCurrent', {})
    if not refs:
        raise ValueError('SPECIALIZED_ASSET_COMPILATION_REQUIRED')
    result = []
    for raw in refs:
        ref = SourcePin.model_validate(raw)
        receipt = host.store.read_ref(ref)
        bible = SpecializedAssetBible.model_validate(receipt['assetBible'])
        if bible.approval_ref is None:
            raise ValueError('SPECIALIZED_ASSET_REVIEW_REQUIRED_FOR_PRODUCTION')
        if bible.work_id != work.id or current.get('specialized-assets:' + work.id) != sha256_canonical(bible):
            raise ValueError('STALE_SPECIALIZED_ASSET')
        originals, resolved = host._inputs(bible, current)
        provider_projection(receipt, originals, resolved)
        result.append(receipt)
    for key in ('visualMedium', 'visualRoute'):
        if key in work.content:
            _check_request_medium(result[0]['medium'], {key: work.content[key]})
    return result


def bind_video_request(work: Any, request: Any) -> Any:
    """Existing VideoRequest consumes exact compiler output and pins; no new provider."""
    from ..contracts.video import VideoRequest
    request = VideoRequest.model_validate(dump_contract(request))
    receipts = require_production_visual_authority(work)
    if request.continuity.work_id != work.id:
        raise ValueError('MOVIE_VISUAL_AUTHORITY_MISMATCH')
    _check_request_medium(receipts[0]['medium'], dump_contract(request.continuity.style))
    refs = [SourcePin.model_validate(value) for value in work.content['specializedAssetCompilationRefs']]
    values = dump_contract(request)
    values['continuity']['sources'] = [dump_contract(ref) for ref in (*request.continuity.sources, *refs)]
    values.pop('authority_context', None)
    context = compile_authority_context(work, values)
    values['prompt'] = request.prompt + '\n' + authority_semantics(context)
    values['authority_context'] = context
    return VideoRequest.model_validate(values)


def compile_authority_context(work: Any, creative_intent: dict[str, Any]) -> dict[str, Any]:
    """Replay approved assets internally; compile only continuity instructions.

    The complete receipt/source map is evidence, not model text. All Work-required
    compilations remain required. Selection is deterministic and source-addressed.
    """
    from copy import deepcopy
    receipts = require_production_visual_authority(work)
    if creative_intent.get('state') == 'CINEMATIC_DIRECTION_FROZEN':
        from ..visual.cinematic import verify_frozen
        spec = verify_frozen(creative_intent)
        if spec.work_id != work.id:
            raise ValueError('MOVIE_VISUAL_AUTHORITY_MISMATCH')
    priorities = {'CHARACTER': ('face', 'body'),
                  'COSTUME': ('garment_structure', 'material'),
                  'SCENE': ('architecture',)}
    assets = []
    for ref, receipt in zip(work.content['specializedAssetCompilationRefs'], receipts, strict=True):
        asset = next(a for a in receipt['assetBible']['assets'] if a['id'] == receipt['assetId'])
        field = next((key for key in priorities[asset['kind']] if key in asset['decisions']), None)
        if field is None:
            raise ValueError('ASSET_EXECUTABLE_SEMANTICS_REQUIRED:' + asset['id'])
        mapping = next((row for row in receipt['sourceMap'] if row.get('assetId') == asset['id'] and row.get('field') == field), None)
        if mapping is None or mapping['text'] != asset['decisions'][field]['text']:
            raise ValueError('ASSET_SOURCE_MAPPING_REQUIRED')
        assets.append({'assetId': asset['id'], 'assetType': asset['kind'],
            'subject': asset.get('characterId', asset.get('sceneId')), 'compiledFrom': deepcopy(ref),
            'compilationFingerprint': sha256_canonical(receipt), 'receipt': deepcopy(receipt),
            'sourceMap': deepcopy(mapping), 'executableSemantic': mapping['text']})
    material = {'schema': 'visual-authority-context-v1', 'workId': work.id,
        'workAuthority': {key: deepcopy(work.content[key]) for key in
                          ('movieVisualMediumRef', 'specializedAssetCompilationRefs', 'visualSourceCurrent')},
        'creativeIntent': deepcopy(creative_intent), 'creativeIntentFingerprint': sha256_canonical(creative_intent),
        'assets': assets}
    return {**material, 'fingerprint': sha256_canonical(material)}


def validate_authority_context(context: dict[str, Any], creative_intent: dict[str, Any], work: Any = None) -> None:
    from types import SimpleNamespace
    if not context:
        raise ValueError('ASSET_AUTHORITY_CONTEXT_REQUIRED')
    owner = work or SimpleNamespace(id=context['workId'], content=context['workAuthority'])
    if context != compile_authority_context(owner, creative_intent):
        raise ValueError('ASSET_AUTHORITY_CONTEXT_CHANGED')


def authority_semantics(context: dict[str, Any]) -> str:
    """Only this derived text may cross the provider prompt boundary."""
    return '\n'.join(f"{row['subject'] if row['assetType'] != 'SCENE' else row['assetId']}({row['assetType']}):{row['executableSemantic']}"
                     for row in context['assets'])


def _check_request_medium(medium: str, value: Any) -> None:
    from ..visual_medium import positive_matches, LIVE, CG
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {'visualMedium', 'visual_medium', 'medium', 'visualRoute', 'visual_route'}:
                allowed = ({'CG', 'CINEMATIC_CG', 'DESIGNED_CG', 'stylized_cinematic_cg'} if medium == 'CG'
                    else {'LIVE_ACTION', 'LIVE_ACTION_PHOTOREAL', 'live_action_realist'})
                if child not in allowed:
                    raise ValueError('MOVIE_MEDIUM_OVERRIDE_FORBIDDEN')
            if key in {'model.prompt_optimization', 'promptEnhancement'} and child not in {'DISABLED', 'disabled', False}:
                raise ValueError('PROVIDER_ENHANCEMENT_NOT_AUTHORIZED')
            _check_request_medium(medium, child)
    elif isinstance(value, list):
        for child in value:
            _check_request_medium(medium, child)
    elif isinstance(value, str) and positive_matches(value, LIVE if medium == 'CG' else CG):
        raise ValueError('MOVIE_MEDIUM_OVERRIDE_FORBIDDEN')


def validate_visual_submission(work: Any, request: dict[str, Any], *, authority_context: dict[str, Any] | None = None,
                               creative_intent: dict[str, Any] | None = None) -> None:
    """Video uses replayable compilation evidence; legacy asset images stay valid."""
    if isinstance(request.get('videoRequest'), dict):
        # HTTP transport envelopes retain the typed request internally; adapters
        # serialize only provider fields. Validate its evidence at the same gate.
        validate_visual_submission(work, request['videoRequest'], authority_context=authority_context,
                                   creative_intent=creative_intent)
        return
    receipts = require_production_visual_authority(work)
    payload = {k: v for k, v in request.items() if k != 'authority_context'}
    _check_request_medium(receipts[0]['medium'], payload)
    prompts: list[str] = []
    def collect(value: Any) -> None:
        if isinstance(value, dict):
            prompts.extend(child for key, child in value.items() if key in {'prompt', 'motion_prompt'} and isinstance(child, str))
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
    collect(payload)
    context = authority_context if authority_context is not None else request.get('authority_context')
    is_video_intent = 'input_mode' in request or 'inputMode' in request
    from ..visual.payload_scope import review_text, asset_payload
    task = 'VIDEO' if is_video_intent or (creative_intent or {}).get('state') == 'CINEMATIC_DIRECTION_FROZEN' else 'IMAGE'
    for prompt in prompts:
        review_text(prompt, task, authority_texts=tuple(r['prompt'] for r in receipts))
    if context is not None or creative_intent is not None or is_video_intent:
        if not context:
            raise ValueError('SUBMISSION_DOES_NOT_CONSUME_SPECIALIZED_ASSETS: ASSET_AUTHORITY_CONTEXT_REQUIRED')
        intent = creative_intent if creative_intent is not None else context['creativeIntent']
        validate_authority_context(context, intent, work)
        if is_video_intent and intent.get('state') != 'CINEMATIC_DIRECTION_FROZEN':
            expected = dict(intent)
            expected['prompt'] = intent['prompt'] + '\n' + authority_semantics(context)
            if payload != expected:
                raise ValueError('ASSET_COMPILED_REPRESENTATION_CHANGED')
        if not prompts or not all(any(row['executableSemantic'] in prompt for prompt in prompts) for row in context['assets']):
            raise ValueError('ASSET_EXECUTABLE_SEMANTICS_MISSING')
        return
    # Image/casting consumers still use complete asset-design prompts. This
    # compatibility branch is never sufficient for a cinematic video frame.
    if not prompts or not all(all(any(line in prompt for prompt in prompts)
                                  for line in asset_payload(receipt)['prompt'].splitlines()) for receipt in receipts):
        raise ValueError('SUBMISSION_DOES_NOT_CONSUME_SPECIALIZED_ASSETS')
