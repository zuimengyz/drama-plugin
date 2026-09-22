"""Offline contract/loop tests. Synthetic review attestations are not artistic validation."""
import json
import hashlib
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from pydantic import ValidationError
from drama_plugin import DramaPlugin
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.director import CapabilityFeedback, CapabilityRequest, DirectorWorkspace
from drama_plugin.contracts.dpd import DPDSnapshot
from drama_plugin.contracts.creation import Scene
from drama_plugin.contracts.sequence import DirectorReviewFacet, FilmReview
from drama_plugin.director import (DirectorError, REPAIR_RESPONSIBILITY, enter, feedback_pin,
    pin, request_pin, trace_intent)
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
from drama_plugin.sequence import film_review_verdict
from test_sequence_production import review as legacy_review, observation
from test_sequence_production import media  # existing local synthetic-clip pytest fixture

ROOT = Path(__file__).resolve().parents[1]


def setup(tmp_path, branch='live-action', approval=False):
    store = DirectorArtifactStore(tmp_path)
    source = pin('scene', {'purpose': 'locked canonical purpose'})
    intent = pin('intent', {'meaning': 'understand consequence'})
    gate = pin('original-approval:' + branch, {'branch': branch, 'issuer': 'fixture user'})
    w = store.create(DirectorWorkspace(workspace_id='film', scope_id='scene', branch_id=branch,
        source_pins=(source,), intent_refs=(intent,)))
    q = CapabilityRequest(request_id='q-' + branch, workspace_id=w.workspace_id,
        branch_id=branch, scope_id=w.scope_id, source_pins=w.source_pins, intent_refs=w.intent_refs,
        capability='shot-design', task='Propose useful coverage', result_kind='DESIGN_ONLY',
        must_preserve=('locked event',), prohibitions=('NO EXTRA DIALOGUE',), priority='HIGH',
        required_evidence=('cause remains readable',), approval_refs=(gate,) if approval else ())
    qref = store.put(request_pin(q).key, dump_contract(q))
    current = {p.key: p.fingerprint for p in (source, intent, gate)}
    w = store.transition(w, 'REQUEST', qref, current)
    result = store.put('existing-owner-result', {'coverageRef': 'existing coverage only'})
    evidence = store.put('design-evidence', {'mode': 'OFFLINE_FIXTURE_ONLY'})
    delta = store.put('presentation-delta', {'domain': 'audience_knowledge', 'summary': 'Design preserves uncertainty', 'presentationOnly': True})
    current.update({p.key: p.fingerprint for p in (result, evidence, delta)})
    f = CapabilityFeedback(request_ref=qref, source_pins=q.source_pins, result_refs=(result,),
        evidence_refs=(evidence,), execution='COMPLETED', feasibility='SUPPORTED',
        fulfilled=q.required_evidence, next_responsibility='Director review')
    return store, w, q, f, delta, current


def observe(store, w, q, f, current):
    ref = store.retain_feedback(q, f)
    return store.transition(w, 'FEEDBACK', ref, current)


def design_review(w, q, f, delta, disposition='APPROVE'):
    facet = DirectorReviewFacet(workspace_id=w.workspace_id, scope_id=w.scope_id, branch_id=w.branch_id,
        source_pins=q.source_pins, intent_refs=q.intent_refs, route_ref=q.route_ref,
        request_ref=request_pin(q), feedback_ref=feedback_pin(f),
        intent_coverage={p.key: 'PASS' if disposition == 'APPROVE' else 'FAIL' for p in q.intent_refs},
        disposition=disposition, reason_summary='Synthetic design judgment, no media observed',
        adopted_delta_ref=delta)
    return {'subjectKind': 'DESIGN_ONLY', 'director': dump_contract(facet), 'findings': []}


def adopt(store, w, q, f, delta, current, disposition='APPROVE', approved_refs=()):
    review = design_review(w, q, f, delta, disposition)
    ref = store.put('bible-review', review)
    return store.transition(w, 'REVIEW', ref, current, approved_refs=approved_refs)


def test_registry_and_readonly_director_surface():
    plugin = DramaPlugin.load(ROOT)
    assert len(plugin.skills.list()) == 57
    assert len(plugin.tools.list()) == 51
    assert all('director' not in t.code for t in plugin.tools.list())
    skill = plugin.skills.get('director')
    assert all('.get_' in name or name == 'context.build_context'
               for name in [*skill.tools.allowed, *skill.tools.preferred])


def test_three_contract_roundtrips_and_unknown(tmp_path):
    _, w, q, f, _, _ = setup(tmp_path)
    for item in (w, q, f):
        assert type(item).model_validate_json(item.model_dump_json()) == item
        assert type(item).model_validate(dump_contract(item)) == item
        with pytest.raises(ValidationError):
            type(item).model_validate({})
        with pytest.raises(ValidationError):
            item.revision = 3
    unknown = CapabilityFeedback(request_ref=request_pin(q), source_pins=q.source_pins,
        next_responsibility='observation')
    assert unknown.feasibility == 'UNKNOWN' and unknown.execution == 'UNKNOWN'
    assert CapabilityFeedback.model_validate(dump_contract(unknown)).feasibility == 'UNKNOWN'


@pytest.mark.parametrize('field', ['fullMedia', 'providerParams', 'prompt', 'seed', 'hiddenReasoning', 'script', 'retryHistory'])
def test_envelopes_reject_implementation_and_duplicated_content(tmp_path, field):
    _, w, q, f, _, _ = setup(tmp_path)
    for item in (w, q, f):
        with pytest.raises(ValidationError):
            type(item).model_validate({**dump_contract(item), field: 'forbidden'})


def test_review_before_adopt_critical_and_sparse_receipt(tmp_path):
    store, w, q, f, delta, current = setup(tmp_path)
    assert enter(w, current, q)['delegate']
    w = store.transition(w, 'DISPATCH', None, current)
    assert store.resume('film', w.branch_id, current)['action'] == 'RECONCILE_RESULT'
    w = observe(store, w, q, f, current)
    assert f.execution == 'COMPLETED' and w.feedback_ref and w.adopted_head is None
    assert store.load('film', w.branch_id).adopted_head is None
    adopted = adopt(store, w, q, f, delta, current)
    receipt = store.read_ref(adopted.adopted_head)
    assert receipt['userApproval'] == 'UNCHANGED'
    assert receipt['subjectKind'] == 'DESIGN_ONLY'
    assert store.resume('film', w.branch_id, current)['action'] == 'NEXT_DECISION'
    assert not any(k in receipt for k in ('subtext', 'objective', 'prompt', 'media'))


def test_no_review_or_forged_head_can_bypass_gate(tmp_path):
    store, w, q, f, delta, current = setup(tmp_path)
    with pytest.raises(DirectorError, match='INSUFFICIENT_EVIDENCE'):
        adopt(store, w, q, f, delta, current)
    with pytest.raises(DirectorError, match='INVALID_SOURCE'):
        store.create(w.model_copy(update={'branch_id': 'forged', 'adopted_head': delta}))
    assert not hasattr(store, 'save')


def test_branch_isolation_both_directions_and_approval_nontransfer(tmp_path):
    a = setup(tmp_path, 'live-action', approval=True)
    b = setup(tmp_path, 'cg', approval=True)
    sa, wa, qa, fa, da, ca = a
    sb, wb, qb, fb, db, cb = b
    wa = observe(sa, wa, qa, fa, ca)
    wb = observe(sb, wb, qb, fb, cb)
    with pytest.raises(DirectorError, match='USER_APPROVAL_REQUIRED'):
        adopt(sb, wb, qb, fb, db, cb, approved_refs=qa.approval_refs)
    wa = adopt(sa, wa, qa, fa, da, ca, approved_refs=qa.approval_refs)
    assert sb.load('film', 'cg').adopted_head is None
    before = sha256_canonical(wa)
    wb = adopt(sb, wb, qb, fb, db, cb, approved_refs=qb.approval_refs)
    assert wa.adopted_head != wb.adopted_head
    assert sha256_canonical(sa.load('film', 'live-action')) == before
    with pytest.raises(DirectorError, match='INVALID_SOURCE'):
        observe(sa, wa, qb, fb, ca)


def test_stale_source_on_resume_blocks_delegation_and_retains_history(tmp_path):
    store, w, q, _, _, current = setup(tmp_path)
    current['scene'] = 'b' * 64
    resumed = store.resume('film', w.branch_id, current)
    assert resumed['action'] == 'STALE_SOURCE' and not resumed['delegate']
    with pytest.raises(DirectorError, match='STALE_SOURCE'):
        store.transition(w, 'DISPATCH', None, current)
    saved = store.load('film', w.branch_id)
    assert saved.stale_keys == ('scene',) and saved.adopted_head is None
    assert len(list((tmp_path / 'history').glob('*.json'))) == 3


def test_resume_recovers_completed_result_before_feedback_checkpoint(tmp_path):
    store, w, q, f, _, current = setup(tmp_path)
    w = store.transition(w, 'DISPATCH', None, current)
    store.retain_feedback(q, f)  # crash here, before workspace feedback checkpoint
    resumed = DirectorArtifactStore(tmp_path).resume('film', w.branch_id, current)
    assert resumed['action'] == 'REVIEW_PENDING' and not resumed['delegate']
    assert resumed['recoveredFeedbackRef'] == dump_contract(feedback_pin(f))
    with pytest.raises(DirectorError, match='REVISION_CONFLICT'):
        store.transition(w, 'DISPATCH', None, current)
    assert store.load('film', w.branch_id).adopted_head is None


def test_concurrent_expected_head_allows_only_one_dispatch(tmp_path):
    store, w, _, _, _, current = setup(tmp_path)
    def attempt(_):
        try:
            DirectorArtifactStore(tmp_path).transition(w, 'DISPATCH', None, current)
            return 'committed'
        except DirectorError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, range(2))) == ['REVISION_CONFLICT', 'committed']


@pytest.mark.parametrize('disposition', [d for d in REPAIR_RESPONSIBILITY if d != 'APPROVE'])
def test_failure_routes_explicitly_and_never_auto_retries(tmp_path, disposition):
    store, w, q, f, delta, current = setup(tmp_path)
    w = observe(store, w, q, f, current)
    w = adopt(store, w, q, f, delta, current, disposition)
    assert w.adopted_head is None and w.checkpoint == 'REVISION_PENDING'
    assert not store.resume('film', w.branch_id, current)['delegate']
    assert REPAIR_RESPONSIBILITY[disposition]


@pytest.mark.parametrize('issue,code', [('unknown', 'CAPABILITY_LIMITATION'), ('unmet', 'INSUFFICIENT_EVIDENCE'),
    ('noevidence', 'INSUFFICIENT_EVIDENCE'), ('approval', 'USER_APPROVAL_REQUIRED'), ('failure', 'EXECUTION_FAILURE')])
def test_approve_cannot_override_feedback_gates(tmp_path, issue, code):
    store, w, q, f, delta, current = setup(tmp_path)
    changes = {'unknown': {'feasibility': 'UNKNOWN'}, 'unmet': {'fulfilled': (), 'unmet': q.required_evidence},
               'noevidence': {'evidence_refs': ()}, 'approval': {'conditions': ('REQUIRES_USER_APPROVAL',)},
               'failure': {'execution': 'FAILED'}}[issue]
    f = CapabilityFeedback.model_validate({**f.model_dump(), **changes})
    w = observe(store, w, q, f, current)
    with pytest.raises(DirectorError, match=code):
        adopt(store, w, q, f, delta, current)
    assert store.load('film', w.branch_id).adopted_head is None


@pytest.mark.parametrize('binding', ['branchId', 'scopeId', 'feedbackRef', 'sourcePins', 'intentRefs'])
def test_wrong_review_binding_rejected(tmp_path, binding):
    store, w, q, f, delta, current = setup(tmp_path)
    w = observe(store, w, q, f, current)
    review = design_review(w, q, f, delta)
    facet = review['director']
    if binding in ('branchId', 'scopeId'):
        facet[binding] = 'wrong'
    elif binding == 'feedbackRef':
        facet[binding]['fingerprint'] = 'b' * 64
    else:
        facet[binding][0]['fingerprint'] = 'b' * 64
    ref = store.put('bad-review', review)
    with pytest.raises(DirectorError, match='INVALID_SOURCE'):
        store.transition(w, 'REVIEW', ref, current)


def test_legacy_film_review_exact_wire_compatibility_and_opt_in_gate(tmp_path):
    raw = legacy_review()
    raw['observations'] = [observation(0, 10, 'NORMAL_AV')]
    legacy = FilmReview(**raw)
    expected = {'mediaHash': 'a'*64, 'duration': 10.0, 'observations': [{
        'start': 0.0, 'end': 10.0, 'mode': 'NORMAL_AV', 'observer': 'Test fixture only', 'evidenceRef': 'fixture'}],
        'findings': [], 'technical': 'PASS', 'storyRhythm': 'PASS', 'visualContinuity': 'PASS',
        'sound': 'PASS', 'persistenceVerified': True}
    assert dump_contract(legacy) == expected
    assert dump_contract(FilmReview.model_validate(expected)) == expected
    assert film_review_verdict(legacy, 'a'*64)['status'] == 'CONTENT_REVIEW_COMPLETE_PENDING_USER_ADOPTION'
    assert film_review_verdict(legacy, 'a'*64, require_director=True)['status'] == 'INSUFFICIENT_EVIDENCE'
    _, w, q, f, delta, _ = setup(tmp_path)
    facet = design_review(w, q, f, delta, 'REVISE_PERFORMANCE')['director']
    reviewed = FilmReview(**raw, director=facet)
    assert reviewed.technical == 'PASS'
    assert film_review_verdict(reviewed, 'a'*64)['status'] == 'REPAIR_REQUIRED'
    assert film_review_verdict(reviewed, 'a'*64)['userAdoption'] == 'UNCHANGED'


def test_intent_chain_and_stale_parent():
    items = []
    for level in ['FILM', 'EPISODE', 'SCENE', 'COVERAGE_GROUP']:
        item = {'id': level.lower(), 'scopeLevel': level, 'meaning': 'existing owner meaning', 'scopeRef': 'scope'}
        if items:
            item['parentRef'] = dump_contract(pin(items[-1]['id'], items[-1]))
        items.append(item)
    assert trace_intent(items, 'coverage_group') == ('coverage_group', 'scene', 'episode', 'film')
    items[0]['meaning'] = 'changed'
    with pytest.raises(DirectorError, match='STALE_SOURCE'):
        trace_intent(items, 'coverage_group')


@pytest.mark.parametrize('scene_no', [2, 8, 7])
def test_real_three_scene_implementation_fixture(tmp_path, scene_no):
    fixture = json.loads((ROOT / 'tests/fixtures/director-three-scenes.json').read_text())
    sample = next(s for s in fixture['samples'] if s['sceneNo'] == scene_no)
    # Validate the actual original DPD; never copy its psychological fields into Workspace.
    dpd = DPDSnapshot.model_validate(sample['dpdSnapshot'])
    assert sha256_canonical(Scene.model_validate(sample['canonicalScene'])) == sample['sourceHash']
    store = DirectorArtifactStore(tmp_path / str(scene_no))
    source = pin(sample['sceneId'], sample['canonicalScene'])
    source.kind = 'CANON'
    intent = store.put('intent', {'sourceRef': dump_contract(source), 'meaning': {
        2: '观众理解选择收缩，楚地已失仍是假设', 8: '看懂仍然有效的帮助与拒绝', 7: '看懂局部突破而非全局胜利'}[scene_no]})
    w = store.create(DirectorWorkspace(workspace_id='gaixia-offline', scope_id=sample['sceneId'],
        branch_id='DESIGN_ONLY', source_pins=(source,), intent_refs=(intent,)))
    q = CapabilityRequest(request_id=f'S{scene_no}', workspace_id=w.workspace_id, scope_id=w.scope_id,
        branch_id=w.branch_id, source_pins=w.source_pins, intent_refs=w.intent_refs,
        capability='video-model-selection' if scene_no == 7 else 'dramatic-performance-direction',
        task={2: '返回唯一DPD；保留报告的不确定性', 8: '保留帮助、拒绝、交缰的次序和距离语义',
              7: '核验地理、接触、归队与再围的覆盖是否可行'}[scene_no], result_kind='DESIGN_ONLY',
        must_preserve=(f'canonical scene {sample["sceneId"]}',),
        prohibitions=('NO TTS REPLACEMENT', 'NO EXTRA DIALOGUE') if scene_no == 8 else ('NO CANON CHANGE',),
        priority='CRITICAL', required_evidence=('source fidelity', 'spatial/relationship legibility'))
    current = {p.key: p.fingerprint for p in (source, intent)}
    w = store.transition(w, 'REQUEST', store.put(request_pin(q).key, dump_contract(q)), current)
    w = store.transition(w, 'DISPATCH', None, current)
    result = store.put('dpd-owner' if scene_no != 7 else 'selection-owner',
        dump_contract(dpd) if scene_no != 7 else {'fixtureOnly': True, 'limitation': 'horse contact + crowd continuity not evidenced'})
    evidence = store.put('fixture-evidence', {'sceneRef': dump_contract(source), 'mode': 'OFFLINE_DESIGN_ONLY'})
    f = CapabilityFeedback(request_ref=request_pin(q), source_pins=q.source_pins, result_refs=(result,),
        evidence_refs=(evidence,), execution='COMPLETED',
        feasibility='REQUIRES_DECOMPOSITION' if scene_no == 7 else 'SUPPORTED',
        fulfilled=() if scene_no == 7 else q.required_evidence,
        unmet=q.required_evidence if scene_no == 7 else (), next_responsibility='Director')
    delta = store.put('sparse-delta', {'domain': 'relationship_presentation' if scene_no == 8 else 'audience_knowledge',
        'summary': {2: '设计采用：楚地是否已失仍未知', 8: '设计采用：帮助先于拒绝，保留原声与可读距离',
                    7: '尚未采用任何战场呈现'}[scene_no], 'presentationOnly': True})
    current.update({p.key: p.fingerprint for p in (result, evidence, delta)})
    w = observe(store, w, q, f, current)
    assert w.adopted_head is None
    disposition = 'ESCALATE_PRODUCTION_METHOD' if scene_no == 7 else 'APPROVE'
    if scene_no == 2:
        # A false certainty is observed/rejected, never promoted to adopted history.
        bad = store.put('bad-delta', {'domain': 'audience_knowledge', 'summary': '楚地已失', 'presentationOnly': True})
        current[bad.key] = bad.fingerprint
        w = adopt(store, w, q, f, bad, current, 'REVISE_PERFORMANCE')
        assert w.adopted_head is None
        q = CapabilityRequest.model_validate({**dump_contract(q), 'revision': 1, 'supersedes': dump_contract(request_pin(q))})
        w = store.transition(w, 'REQUEST', store.put(request_pin(q).key, dump_contract(q)), current)
        f = CapabilityFeedback.model_validate({**dump_contract(f), 'requestRef': dump_contract(request_pin(q))})
        w = observe(store, w, q, f, current)
    w = adopt(store, w, q, f, delta, current, disposition)
    if scene_no == 7:
        assert w.adopted_head is None
        proposed = CapabilityRequest.model_validate({**dump_contract(q), 'revision': 1,
            'supersedes': dump_contract(request_pin(q)), 'capability': 'shot-design',
            'task': '提出地理建立、局部接触、突围后果与再围的覆盖分解；保留原Scene和现有Shot'})
        assert proposed.capability == 'shot-design'
        assert not store.resume(w.workspace_id, w.branch_id, current)['delegate']
    else:
        assert w.adopted_head is not None
        assert 'subtext' not in dump_contract(w) and 'objective' not in dump_contract(w)
        assert store.read_ref(delta)['summary'].startswith('设计采用')
    if scene_no == 8:
        assert 'NO TTS REPLACEMENT' in q.prohibitions


def test_waiting_original_approval_is_durable_and_resumable(tmp_path):
    store, w, q, f, _, current = setup(tmp_path, approval=True)
    with pytest.raises(DirectorError, match='USER_APPROVAL_REQUIRED'):
        store.transition(w, 'DISPATCH', None, current)
    w = store.load('film', w.branch_id)
    assert store.resume('film', w.branch_id, current)['action'] == 'WAITING_APPROVAL'
    w = store.transition(w, 'DISPATCH', None, current, approved_refs=q.approval_refs)
    assert w.checkpoint == 'DISPATCHED'
    assert w.adopted_head is None


def test_media_adoption_requires_real_review_shape_and_qc_coverage(tmp_path, media):
    store, w, q, _, delta, current = setup(tmp_path)
    # Fresh branch because a request kind is immutable after issue.
    w = store.create(DirectorWorkspace(workspace_id='film', scope_id=w.scope_id, branch_id='media-fixture',
        source_pins=w.source_pins, intent_refs=w.intent_refs))
    q = CapabilityRequest.model_validate({**dump_contract(q), 'requestId': 'media-fixture',
        'branchId': w.branch_id, 'resultKind': 'MEDIA'})
    w = store.transition(w, 'REQUEST', store.put(request_pin(q).key, dump_contract(q)), current)
    _, clips, _ = media
    clip = clips['red']
    duration = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(clip)]))
    media_ref = pin('synthetic-media-fixture', {})
    media_ref.kind = 'MEDIA'
    media_ref.fingerprint = hashlib.sha256(clip.read_bytes()).hexdigest()
    evidence = pin('synthetic-attestation', {'fixtureOnly': True})
    current.update({p.key: p.fingerprint for p in (media_ref, evidence)})
    f = CapabilityFeedback(request_ref=request_pin(q), source_pins=q.source_pins, result_refs=(media_ref,),
        evidence_refs=(evidence,), execution='COMPLETED', feasibility='SUPPORTED', fulfilled=q.required_evidence,
        next_responsibility='Director')
    w = observe(store, w, q, f, current)
    # Actual local synthetic clip; observation entries are test attestations only.
    # No formal Media, film observation or artistic validation is claimed.
    raw = legacy_review(); raw['media_hash'] = media_ref.fingerprint; raw['duration'] = duration
    raw['director'] = design_review(w, q, f, delta)['director']
    with pytest.raises(DirectorError, match='INSUFFICIENT_EVIDENCE'):
        store.transition(w, 'REVIEW', store.put('film-review', dump_contract(FilmReview(**raw))), current)
    raw['observations'] = [observation(0, duration, 'NORMAL_AV')]
    passed = store.transition(w, 'REVIEW', store.put('film-review', dump_contract(FilmReview(**raw))), current)
    assert passed.adopted_head
    assert store.read_ref(passed.adopted_head)['userApproval'] == 'UNCHANGED'


def test_design_review_cannot_hide_unresolved_bible_findings(tmp_path):
    store, w, q, f, delta, current = setup(tmp_path)
    w = observe(store, w, q, f, current)
    review = design_review(w, q, f, delta)
    review['findings'] = [{'id': 'canon-conflict', 'severity': 'MAJOR', 'resolved': False}]
    with pytest.raises(DirectorError, match='UPSTREAM_REVIEW_REQUIRED'):
        store.transition(w, 'REVIEW', store.put('bible-review', review), current)


def test_route_change_and_observed_bytes_change_require_revalidation(tmp_path):
    store, w, q, f, _, current = setup(tmp_path)
    changed = CapabilityRequest.model_validate({**dump_contract(q), 'routeRef': dump_contract(pin('cg', {'route': 'cg'}))})
    with pytest.raises(DirectorError, match='INVALID_SOURCE'):
        enter(w, current, changed)
    w = observe(store, w, q, f, current)
    current[f.result_refs[0].key] = 'f' * 64
    assert store.resume('film', w.branch_id, current)['action'] == 'STALE_SOURCE'


def test_artifact_tamper_and_nested_pin_mutation_cannot_bypass_cas(tmp_path):
    store, w, q, _, _, current = setup(tmp_path)
    qref = request_pin(q)
    # SourcePin is an existing mutable contract; boundary revalidation/CAS protects nested mutation.
    w.source_pins[0].fingerprint = 'f' * 64
    with pytest.raises(DirectorError, match='REVISION_CONFLICT'):
        store.transition(w, 'DISPATCH', None, current)
    obj = store._path('objects', qref.fingerprint)
    obj.write_text('{"tampered":true}')
    with pytest.raises(DirectorError, match='INVALID_SOURCE'):
        store.read_ref(qref)


def test_revision_branch_has_parent_but_never_inherits_adoption(tmp_path):
    store, w, q, f, delta, current = setup(tmp_path, 'revision-A')
    w = observe(store, w, q, f, current)
    w = adopt(store, w, q, f, delta, current)
    parent = store.put('revision-A-head', dump_contract(w))
    b = store.create(DirectorWorkspace(workspace_id=w.workspace_id, scope_id=w.scope_id, branch_id='revision-B',
        parent_ref=parent, source_pins=w.source_pins, intent_refs=w.intent_refs))
    assert b.parent_ref == parent and b.adopted_head is None and b.review_ref is None
    assert store.load(w.workspace_id, w.branch_id).adopted_head == w.adopted_head
