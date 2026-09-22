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
            values=department_values(bible, identity, department),
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
    values['prompt'] = request.prompt + '\n' + '\n'.join(receipt['prompt'] for receipt in receipts)
    values['continuity']['sources'] = [dump_contract(ref) for ref in (*request.continuity.sources, *refs)]
    return VideoRequest.model_validate(values)


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


def validate_visual_submission(work: Any, request: dict[str, Any]) -> None:
    """A valid unrelated Bible is not sufficient: the submitted prompt must consume it."""
    receipts = require_production_visual_authority(work)
    _check_request_medium(receipts[0]['medium'], request)
    prompts: list[str] = []
    def collect(value: Any) -> None:
        if isinstance(value, dict):
            prompts.extend(child for key, child in value.items() if key in {'prompt', 'motion_prompt'} and isinstance(child, str))
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
    collect(request)
    if not prompts or not all(any(receipt['prompt'] in prompt for prompt in prompts) for receipt in receipts):
        raise ValueError('SUBMISSION_DOES_NOT_CONSUME_SPECIALIZED_ASSETS')
