"""Official Host -> real begin-submission authority, with no network or spending."""
from copy import deepcopy
from pathlib import Path
from typing import Any
import json
import pytest
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.creation import Work
from drama_plugin.hosts import http_video, route_production
from drama_plugin.hosts.specialized_asset import bind_video_request
from drama_plugin.visual import production
from r3d_r_helpers import blocker_case
from r3d_helpers import case, approval
from test_official_video_providers import request, config, resolve
from test_production_route import route


@pytest.mark.asyncio
async def test_http_submit_forwards_trust_to_real_formal_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    x=blocker_case(tmp_path,medium='cg'); h=x['host']; b=x['candidate']; cur=x['current']; refs=(x['trusted'],)
    review=h.store.put('asset-review:rt04',dict(kind='SPECIALIZED_ASSET_REVIEW',decision='APPROVE',workId='work',reviewer='offline',
        checkedBoundaries=['DRAMATURGY','DIRECTOR_INTENT','SOURCE_WORLD','GLOBAL_STYLE'],subjectFingerprint=fp(dump_contract(b,exclude={'approval_ref'}))))
    cur[review.key]=review.fingerprint;b=b.model_copy(update={'approval_ref':review})
    pin=h.submit(b,current=cur,approved_interpretation_refs=refs);cur[pin.key]=pin.fingerprint
    compilation=h.compile(pin,'char',current=cur,approved_interpretation_refs=refs)
    monkeypatch.setenv('DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT',str(tmp_path))
    work=Work(id='work',title='Offline',content={'movieVisualMediumRef':dump_contract(b.runtime_ref),
        'specializedAssetCompilationRefs':[compilation['compilationRef']],'visualSourceCurrent':cur})
    v=request()  # type: ignore[no-untyped-call]
    v.continuity.work_id='work'
    from drama_plugin.visual.video_prompt import ir_source_fingerprint
    v=v.model_copy(update={'prompt_ir':{**v.prompt_ir,'source_fingerprint':ir_source_fingerprint(v)}})
    v=bind_video_request(work,v,approved_interpretation_refs=refs)
    envelope={'provider':'seedance','model':v.continuity.primary_model,'videoRequest':dump_contract(v)}
    binding={k:'offline' for k in ('execution','endpoint_fingerprint','provider_schema_fingerprint','operation')}
    frame: dict[str, Any] = {'spec':{}}  # Existing authority-context fallback, not the still-only mapper.
    attempt={'attempt_id':'offline','shot_id':'shot','status':'RESERVED','job_id':None,'request':envelope,'execution_binding':binding,'frame_snapshot':frame}
    raw=route(tmp_path).model_dump(mode='json')  # type: ignore[no-untyped-call]
    raw['work_id']='work';work.content.update(productionRoute=raw,productionStage={'frames':{'shot':frame},'attempts':[attempt]})
    class Memory:
        async def get_work(self, work_id: str) -> Work:return deepcopy(work)
        async def save_work(self,*args: Any) -> None:raise AssertionError('No ledger write in pre-submit probe')
    class Provider:
        async def materialize(self,*args: Any) -> None:pass
        async def create_task(self,*args: Any,**kwargs: Any) -> None:raise AssertionError('No paid call')
        async def aclose(self) -> None:pass
    host=http_video.VideoProviderHost(Memory(),None,None,tmp_path/'cache',configuration={})
    async def retained(*args: Any) -> dict[str, Any]:return deepcopy(attempt)
    async def bound(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return binding
    async def provider(*args: Any) -> Provider:return Provider()
    async def jurisdiction(*args: Any) -> None:pass
    class AdmissionPassed(Exception):pass
    def stop(*args: Any,**kwargs: Any) -> None:raise AdmissionPassed
    monkeypatch.setattr(host,'_attempt',retained);monkeypatch.setattr(host,'bind',bound);monkeypatch.setattr(host,'_provider',provider)
    monkeypatch.setattr(http_video,'verify_execution',lambda *args, **kwargs:None)
    import drama_plugin.config.video_route as runtime_route
    import drama_plugin.production_language as language
    monkeypatch.setattr(runtime_route,'require_runtime_route',lambda *args:None)
    monkeypatch.setattr(language,'require_native_video_submission',lambda *args:None)
    monkeypatch.setattr(route_production,'validate_route_direction_sources',jurisdiction)
    monkeypatch.setattr(route_production,'attempt_frame',lambda state,a:frame)
    monkeypatch.setattr(production,'check_campaign',lambda state:None)
    monkeypatch.setattr(production,'begin_submission',stop)
    # The real operate -> validate_visual_submission -> validate_consumption chain runs.
    with pytest.raises(AdmissionPassed):await host.submit('work','offline',approved_interpretation_refs=refs)
    other=case(identity='other');wrong=approval(other)
    cross=deepcopy(x['c']['artifacts'][x['trusted'].key]);cross['workRef']='OTHER'
    cross_pin=h.store.put(x['trusted'].key,cross)
    for invalid in [(),(wrong,),(cross_pin,)]:
        with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):
            await host.submit('work','offline',approved_interpretation_refs=invalid)
    # Even forged provenance on the Work is not caller execution authority.
    work.content['approved_interpretation_refs']=[dump_contract(p) for p in refs]
    with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):await host.submit('work','offline')
    from drama_plugin.providers.video.adapters import SeedanceProvider
    adapter=SeedanceProvider(v.continuity.primary_model,config('seedance'),resolve=resolve)  # type: ignore[no-untyped-call]
    try:
        wire=json.dumps(adapter.payload(v,{},'offline'))
        for token in ['approved_interpretation_refs','interpretationUses','approval_ref',x['trusted'].key,x['c']['item']['meaning']]:assert token not in wire
    finally:await adapter.aclose()
