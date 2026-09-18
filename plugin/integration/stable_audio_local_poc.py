"""Work-specific Gaixia integration EXAMPLE/TEST HARNESS; not a generic default.
Host-owned local qualification and two-candidate PoC. No formal writes."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import wave
from typing import Any

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / 'src'))
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.contracts.film_score import FilmScorePlan
from drama_plugin.contracts.performance_direction import DirectorPerformanceIntent
from drama_plugin.music_direction import composer_brief, review_score_plan
from drama_plugin.providers.music.stable_audio import (
    LocalConfig, StableAudio3Provider, StableAudio3CloudRoute, digest, inspect_wav,
    write_json, map_brief, run_local, validate_inputs, qualify,
)


def inputs(foundation: Path, proposal: Path) -> tuple[Any, ...]:
    plan = FilmScorePlan.model_validate_json((foundation / 'contracts/gaixia-film-score-plan.json').read_text())
    briefs = json.loads((foundation / 'contracts/composer-briefs.json').read_text())
    brief = next(b for b in briefs if b['cueRef'] == 'C03')
    intents = {k:DirectorPerformanceIntent.model_validate(v) for k,v in json.loads((foundation / 'contracts/gaixia-performance-intents.json').read_text()).items()}
    current = {'r1-proposal':digest(proposal), 'historical-verse-policy':digest(foundation / 'historical-verse-performance-policy.md')}
    current['gaixia-score-director-intent'] = fp({'source':current['r1-proposal'], 'thesis':'集体行动如何接续、断裂，个人能力如何只能完成局部兑现', 'policy':current['historical-verse-policy']})
    current.update({'performance:'+k:fp(v) for k,v in intents.items()})
    review = review_score_plan(plan, current=current, expected_scene_ids=list(intents), performance_intents=intents,
                              excluded_performance_refs=plan.excluded_performance_refs)
    if review['status'] != 'SCORE_DESIGN_REVIEW_READY':
        raise ValueError('SCORE_REVIEW_FAILED')
    r = next(c.generation_requirements for c in plan.music_cues if c.cue_id == 'C03')
    assert r is not None
    validate_inputs(plan, r, brief, current, fp(brief))
    return plan, r, brief, current, review


def compare_regions(original: Path, result: Path, start: float, end: float) -> dict[str, Any]:
    def read(p: Path) -> tuple[bytes, int, int]:
        with wave.open(str(p), 'rb') as w:
            return w.readframes(w.getnframes()), w.getframerate(), w.getnchannels()*w.getsampwidth()
    a, rate, frame_bytes = read(original)
    b, rate_b, frame_bytes_b = read(result)
    assert (rate, frame_bytes) == (rate_b, frame_bytes_b)
    left, right = round(start*rate)*frame_bytes, round(end*rate)*frame_bytes
    regions = {'before':(a[:left], b[:left]), 'after':(a[right:], b[right:len(a)])}
    return {name:{'sourceHash':hashlib.sha256(x).hexdigest(), 'resultHash':hashlib.sha256(y).hexdigest(),
                  'pcmBitExact':x == y, 'bytesCompared':len(x)} for name,(x,y) in regions.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--foundation', type=Path, required=True)
    ap.add_argument('--proposal', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--mode', choices=['inspect', 'probe', 'candidates'], required=True)
    args = ap.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    (out/'audio').mkdir(exist_ok=True); (out/'validation').mkdir(exist_ok=True)
    config = LocalConfig.from_env(); provider = StableAudio3Provider(config, out)
    installation = provider.inspect_capabilities()
    plan, r, brief, current, review = inputs(args.foundation, args.proposal)
    translation = json.loads((out/'c03-translation.json').read_text())
    # Work-specific exclusion example, kept outside the reusable adapter.
    translation['protectedPerformanceTexts'] = ['力拔山', '氣蓋世', '气盖世', '時不利', '时不利', '騅不逝', '骓不逝', '虞兮', '奈若何']
    mapping = map_brief(brief, translation)
    write_json(out/'validation/source-binding.json', {'package':str(PACKAGE), 'planFingerprint':fp(plan),
        'composerBriefFingerprint':fp(brief), 'requirementsFingerprint':fp(r), 'current':current,
        'review':review, 'sourceKind':plan.source_kind, 'userMusicApproval':False})
    write_json(out/'validation/adapter-mapping.json', mapping)
    write_json(out/'cloud-boundary.json', StableAudio3CloudRoute().inspect_capabilities())
    # Actual installed negative tests, using real source rather than only synthetic fixtures.
    negatives = {}
    for ref in (*plan.excluded_performance_refs, 'P03:NO_SCORE'):
        try:
            composer_brief(plan, ref, current=current)
        except ValueError as exc:
            negatives[ref] = str(exc)
        else:
            raise AssertionError('NEGATIVE_TEST_ACCEPTED')
    write_json(out/'validation/installed-negative-tests.json', negatives)
    if args.mode == 'inspect':
        write_json(out/'local-installation.json', installation)
        print(json.dumps({'package':str(PACKAGE), 'binding':installation['binding'], 'discovered':True}))
        return
    if args.mode == 'probe':
        # Qualification clips are explicitly distinct from the two primary C03 candidates.
        # Short probe uses the same semantic target, as a technical subrange test only.
        short = out/'audio/probe-short.wav'
        metrics = run_local(config,out,'probe-short',mapping,duration=12,seed=70301,output=short)
        meta = inspect_wav(short,12)
        if not meta['durationPass'] or not meta['nonSilent']:
            raise ValueError('LOCAL_POC_BASELINE_FAILED')
        installation.update(modelLoaded=True, pythonVersion=metrics['pythonVersion'], runtime=metrics)
        write_json(out/'local-installation.json', installation)
        write_json(out/'validation/probe-short-metadata.json',meta)
        poc = {'binding':installation['binding'], 'modelLoaded':True, 'wavValid':True,
               'durationValid':True, 'offline':metrics['networkAttempts']==0, 'instrumentalTargetExecuted':True,
               'instrumentalVerified':'UNKNOWN', 'listening':'REQUIRES_HUMAN_LISTENING'}
        write_json(out/'validation/poc-baseline.json',poc)
        optional = {}
        if installation['encoderPresent']:
            for name,seconds,window,noise in [('reference',12,None,.65), ('inpaint',12,(4.,6.),1.), ('extend',15,(12.,15.),1.)]:
                target = out/'audio'/('probe-'+name+'.wav')
                execution = run_local(config,out,'probe-'+name,mapping,duration=seconds,seed=70302,output=target,
                                      init_audio=short,edit_window=window,noise=noise)
                details = {'execution':execution, 'metadata':inspect_wav(target,seconds),
                           'technicalInterface':'PASS', 'artisticContinuity':'HUMAN_REVIEW_REQUIRED',
                           'source':str(short), 'sourceHash':digest(short), 'requestedEditWindow':window}
                if window:
                    details['unchangedRegions'] = compare_regions(short,target,*window)
                optional[name] = details
        write_json(out/'validation/optional-probes.json',optional)
        statuses = dict.fromkeys(['instrumental_control','structural_control','continuation','revision',
            'motif_consistency','forced_vocals_risk','commercial_rights','prompt_fidelity'], 'UNKNOWN')
        statuses.update(duration_control='PASS', lossless_export='PASS', cost_observability='PASS',
                        performance_observability='PASS', stems='NOT_SUPPORTED',
                        reference_audio='PASS' if 'reference' in optional else 'NOT_SUPPORTED')
        if not optional:
            statuses.update(continuation='NOT_SUPPORTED',revision='NOT_SUPPORTED')
        evidence = {'binding':installation['binding'], 'route':'LOCAL', 'statuses':statuses,
                    'stemsKind':'NONE', 'stemsA':'UNKNOWN_SINGLE_INSTRUMENT_PROMPT_NOT_PROBED',
                    'stemsB':'NOT_SUPPORTED', 'optionalProbeEvidence':str(out/'validation/optional-probes.json'),
                    'durationScope':'12s technical probe; C03 range measurement follows with candidates',
                    'seed':'PASS', 'referenceMode':'audio-to-audio initialization, not guaranteed motif conditioning'}
        write_json(out/'capabilities.json',evidence)
        write_json(out/'qualification.json',qualify(plan,r,installation,evidence))
        print(json.dumps({'modelLoaded':True,'optionalProbes':list(optional),'productionQualification':'BLOCKED'}))
        return
    qualification = json.loads((out/'qualification.json').read_text())
    poc = json.loads((out/'validation/poc-baseline.json').read_text())
    for name,seed in [('A',83001),('B',83002)]:
        result = provider.generate(plan,r,brief,current=current,reviewed_brief=fp(brief),translation=translation,
            qualification=qualification,poc_evidence=poc,state='LOCAL_ENGINEERING_POC',candidate=name,duration=27,seed=seed)
        assert provider.get_result(name)['sha256'] == result['sha256']
        print(json.dumps({'candidate':name,'status':result['status'],'wallSeconds':result['wallSeconds']}),flush=True)


if __name__ == '__main__':
    main()
