"""Creative runtime accounting only; no media duration, default length or route choice."""
from typing import Any, Mapping, Sequence
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.director import DirectorRuntimeEstimate


def review_runtime(estimate: DirectorRuntimeEstimate | None, *, scene_ids: Sequence[str],
                   current: Mapping[str,str]) -> dict[str,Any]:
    if estimate is None:raise ValueError('DIRECTOR_RUNTIME_ESTIMATE_REQUIRED')
    estimate=DirectorRuntimeEstimate.model_validate(dump_contract(estimate))
    if len(scene_ids)!=len(set(scene_ids)) or set(scene_ids)!={r.scene_id for r in estimate.scene_budgets}:
        raise ValueError('RUNTIME_SCENE_COVERAGE_MISMATCH')
    if any(current.get(r.source_ref.key)!=r.source_ref.fingerprint for r in estimate.scene_budgets):
        raise ValueError('STALE_RUNTIME_SOURCE')
    fields=('dialogue_seconds','action_seconds','silent_performance_seconds','transition_seconds','music_bearing_seconds','intentional_no_music_seconds','music_undecided_seconds')
    sequences: dict[str,float]={};acts: dict[str,float]={}
    for row in estimate.scene_budgets:
        sequences[row.sequence_id]=sequences.get(row.sequence_id,0)+row.expected_seconds
        acts[row.act_id]=acts.get(row.act_id,0)+row.expected_seconds
    return {'status':'CREATIVE_RUNTIME_ACCOUNTED','fingerprint':sha256_canonical(estimate),
            'targetSeconds':estimate.target_seconds,'expectedRangeSeconds':estimate.expected_range_seconds,
            'sequenceSeconds':sequences,'actSeconds':acts,'totals':{f:sum(getattr(r,f) for r in estimate.scene_budgets) for f in fields},
            'actualMediaDuration':None,'artisticApproval':False,'productionAuthorized':False}
