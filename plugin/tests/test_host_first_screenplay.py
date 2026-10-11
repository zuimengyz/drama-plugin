"""Creation order, immutable originals, Host choice and non-adjacent context."""
from pathlib import Path
import socket

import pytest

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.base import dump_contract
from drama_plugin.creative_engine.screenplay import ContextOriginal, NarrativeThread
from drama_plugin.creative_engine.backends import FormalCanonAuthor
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
from drama_plugin.creative_engine.screenplay import ScreenplayWorkshop
from drama_plugin.providers.mock import MockDramaData

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def plugin(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Text creation test must not call a service/provider')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)
    monkeypatch.setattr('drama_plugin.plugin.load_config', lambda _: DramaPluginConfig())
    return DramaPlugin.load(ROOT, mock_data=MockDramaData(), creative_root=tmp_path / 'creative')


async def begin(plugin, session='scene-v1', scene='12'):
    source = await plugin.tools.invoke('screenplay.retain_context', original=ContextOriginal(
        work_id='work', label='complete-original', status='DESIGNATED_SOURCE', text='Complete source.'))
    film = await plugin.tools.invoke('screenplay.retain_context', original=ContextOriginal(
        work_id='work', label='adopted-full-film', status='ADOPTED_FACT', text='Full film: scenes 2, 7, 12.',
        authority_ref='existing-adopted-script-version'))
    packet = await plugin.tools.invoke('screenplay.begin', session_id=session, work_id='work',
        scope='SCENE', scene_id=scene, goal='Write the whole scene freely.', source_refs=(source, film), full_film_ref=film)
    return packet, source, film


async def test_registered_entry_has_no_prewriting_professional_bundle(plugin):
    packet, _, _ = await begin(plugin)
    assert packet['authorPacket']['professionalGuidance'] == []
    assert packet['authorPacket']['historicalCandidates'] == []
    assert len(packet['authorPacket']['sources']) == 2
    assert packet['session']['originalV1Ref'] is None
    with pytest.raises(ValueError, match='preserve V1'):
        await plugin.tools.invoke('screenplay.support_packet', session_id='scene-v1', specialty='sound', question='Study timing.')
    with pytest.raises(ValueError, match='preserve V1'):
        await plugin.tools.invoke('screenplay.retain_support', session_id='scene-v1', specialty='sound', text='Advice.', expected_revision=0)
    with pytest.raises(ValueError, match='preserve V1'):
        await plugin.tools.invoke('screenplay.decide', session_id='scene-v1', choice='KEEP_ALL', reason='Keep it.', expected_revision=0)


async def test_host_can_reject_advice_and_keep_exact_original(plugin):
    await begin(plugin)
    text = '\nComplete scene.\nA hand is raised, then remains.  \n'
    original = await plugin.tools.invoke('screenplay.retain_v1', session_id='scene-v1', text=text)
    advice = await plugin.tools.invoke('screenplay.support_packet', session_id='scene-v1', specialty='editorial', question='Explore its duration.')
    assert advice['original']['text'] == text
    await plugin.tools.invoke('screenplay.retain_support', session_id='scene-v1', specialty='editorial',
        text='A shorter version would improve local pace but lose accumulation.', expected_revision=1)
    selected = await plugin.tools.invoke('screenplay.decide', session_id='scene-v1', choice='KEEP_ALL',
        reason='The accumulated relation is the whole scene; reject local shortening.', expected_revision=2)
    assert selected == original
    handoff = await plugin.tools.invoke('screenplay.shot_handoff', session_id='scene-v1')
    assert handoff['screenplay']['text'] == text
    assert handoff['use'] == 'TEXT_DESIGN_ONLY' and handoff['formalAdoptionRequired']
    assert plugin.screenplays.load('scene-v1').support_refs
    with pytest.raises(ValueError, match='immutable'):
        await plugin.tools.invoke('screenplay.retain_v1', session_id='scene-v1', text='Replacement.')


async def test_revisions_are_complete_versions_and_stale_writer_cannot_select(plugin):
    await begin(plugin)
    original = await plugin.tools.invoke('screenplay.retain_v1', session_id='scene-v1', text='Full original.')
    with pytest.raises(ValueError, match='revision conflict'):
        await plugin.tools.invoke('screenplay.decide', session_id='scene-v1', choice='KEEP_ALL', reason='Keep.', expected_revision=0)
    changed = await plugin.tools.invoke('screenplay.decide', session_id='scene-v1', choice='DEVELOP',
        reason='Develop the unheard answer.', text='Full developed scene.', expected_revision=1)
    assert changed != original
    assert plugin.screenplays.objects.read_ref(original)['text'] == 'Full original.'
    assert plugin.screenplays.shot_handoff('scene-v1')['screenplay']['text'] == 'Full developed scene.'
    back = await plugin.tools.invoke('screenplay.decide', session_id='scene-v1', choice='KEEP_ALL', reason='Return to the original.', expected_revision=2)
    assert back == original


async def test_memory_reaches_nonadjacent_scenes_without_mandatory_payoff(plugin):
    _, source, film = await begin(plugin)
    thread = await plugin.tools.invoke('screenplay.retain_thread', thread=NarrativeThread(
        work_id='work', key='changing-knowledge', status='ADOPTED_FACT', account='An action is understood differently in scenes 2, 7 and 12.',
        scene_ids=('2', '7', '12'), tags=('knowledge',), source_refs=(film,)))
    open_source = await plugin.tools.invoke('screenplay.retain_context', original=ContextOriginal(
        work_id='work', label='possible-future', status='OPEN_POSSIBILITY', text='A possible later association.'))
    possible = await plugin.tools.invoke('screenplay.retain_thread', thread=NarrativeThread(
        work_id='work', key='unassigned', status='OPEN_POSSIBILITY', account='No scheduled return is necessary.',
        scene_ids=('12',), source_refs=(open_source,)))
    packet = await plugin.tools.invoke('screenplay.begin', session_id='long-arc', work_id='work', scope='SCENE', scene_id='12',
        goal='Create freely from the complete work.', source_refs=(source, film), full_film_ref=film)
    rows = packet['authorPacket']['longArcMemory']
    assert [r['ref'] for r in rows] == [dump_contract(thread)]
    assert rows[0]['sceneIds'] == ['2', '7', '12']
    packet2 = await plugin.tools.invoke('screenplay.begin', session_id='long-arc-open', work_id='work', scope='SCENE', scene_id='12',
        goal='Consider this open association.', source_refs=(source, film), full_film_ref=film, memory_refs=(possible,))
    assert {r['status'] for r in packet2['authorPacket']['longArcMemory']} == {'ADOPTED_FACT', 'OPEN_POSSIBILITY'}
    assert all(r['possibleReturnScene'] is None for r in packet2['authorPacket']['longArcMemory'])
    with pytest.raises(ValueError, match='cannot become'):
        await plugin.tools.invoke('screenplay.retain_thread', thread=NarrativeThread(
            work_id='work', key='false-canon', status='ADOPTED_FACT', account='Hypothesis.', source_refs=(open_source,)))


def test_first_native_author_can_create_with_no_craft_files(tmp_path):
    author = FormalCanonAuthor(object(), tmp_path / 'absent-skills')
    # This would fail if initial authoring still loaded the old craft bundles.
    assert author.system_contract(film=True)
    assert author.system_contract()


def test_context_status_and_work_isolation(tmp_path):
    w = ScreenplayWorkshop(DirectorArtifactStore(tmp_path))
    with pytest.raises(ValueError, match='authority reference'):
        ContextOriginal(work_id='a', label='fact', status='ADOPTED_FACT', text='Fact.')
    with pytest.raises(ValueError, match='observation evidence'):
        ContextOriginal(work_id='a', label='seen', status='OBSERVED_RESULT', text='Unseen.')
    source = w.retain_context(ContextOriginal(work_id='a', label='source', status='DESIGNATED_SOURCE', text='Source.'))
    with pytest.raises(ValueError, match='work mismatch'):
        w.begin(session_id='wrong', work_id='b', scope='FILM', goal='Write.', source_refs=(source,))
    with pytest.raises(ValueError, match='complete film framework'):
        w.begin(session_id='missing-film', work_id='a', scope='SCENE', scene_id='4', goal='Write.', source_refs=(source,))


def test_authored_film_framework_remains_candidate_when_used_for_scene(tmp_path):
    w = ScreenplayWorkshop(DirectorArtifactStore(tmp_path))
    film = w.retain_context(ContextOriginal(work_id='a', label='Host-film-V1', status='AUTHOR_CONCEPT', text='Complete unadopted film.'))
    packet = w.begin(session_id='new-film-scene', work_id='a', scope='SCENE', scene_id='4', goal='Write.', source_refs=(film,), full_film_ref=film)
    assert packet['authorPacket']['sources'][0]['status'] == 'AUTHOR_CONCEPT'
    assert packet['session']['selectedRef'] is None


def test_film_cannot_skip_scene_layer_and_invalid_decision_is_not_retained(tmp_path):
    w = ScreenplayWorkshop(DirectorArtifactStore(tmp_path))
    source = w.retain_context(ContextOriginal(work_id='a', label='source', status='DESIGNATED_SOURCE', text='Whole source.'))
    w.begin(session_id='film', work_id='a', scope='FILM', goal='Write.', source_refs=(source,))
    w.retain_v1('film', 'Whole film.')
    with pytest.raises(ValueError, match='Unsupported Host'):
        w.decide('film', choice='TYPO', reason='Invalid.', text='Changed.', expected_revision=1)
    assert w.load('film').revision == 1 and not w.load('film').decision_refs
    w.decide('film', choice='KEEP_ALL', reason='Keep the complete film.', expected_revision=1)
    with pytest.raises(ValueError, match='Complete a scene'):
        w.shot_handoff('film')


def test_memory_evolves_without_erasing_previous_originals(tmp_path):
    w = ScreenplayWorkshop(DirectorArtifactStore(tmp_path))
    source = w.retain_context(ContextOriginal(work_id='a', label='adopted', status='ADOPTED_FACT', text='Source.', authority_ref='existing-owner-v1'))
    prior = w.retain_thread(NarrativeThread(work_id='a', key='line', status='ADOPTED_FACT', account='Earlier account.', scene_ids=('2','7','12'), source_refs=(source,)))
    latest = w.retain_thread(NarrativeThread(work_id='a', key='line', status='ADOPTED_FACT', account='Later account.', scene_ids=('2','7','12'), source_refs=(source,)))
    rows = w.relevant_memory('a','12')
    assert len(rows) == 1 and rows[0]['ref']['fingerprint'] == latest.fingerprint and rows[0]['current']
    historical = w.relevant_memory('a','12', include_refs=(prior,), only_refs=True)
    assert len(historical) == 1 and historical[0]['account'] == 'Earlier account.' and not historical[0]['current']
    assert w.objects.read_ref(prior)['account'] == 'Earlier account.'
    concept = w.retain_context(ContextOriginal(work_id='a', label='possible', status='AUTHOR_CONCEPT', text='Candidate.'))
    w.retain_thread(NarrativeThread(work_id='a', key='line', status='AUTHOR_CONCEPT', account='Unadopted new idea.', scene_ids=('12',), source_refs=(concept,)))
    assert w.relevant_memory('a','12')[0]['ref']['fingerprint'] == latest.fingerprint



@pytest.mark.asyncio
async def test_native_scene_failure_retains_v1_without_completing_direction(plugin):
    from test_formal_author_backends import canon, source
    from drama_plugin.creative_engine.backends import HostSceneOriginal, HostScreenplayDecision
    from drama_plugin.creative_engine.contracts import Authority, CreativeCheckpoint, Kind
    from drama_plugin.runtime.contracts import CapabilityInput, RunMode
    calls = []
    class TextOnlyClient:
        async def complete(self, role, system, request, result, **kwargs):
            identity = kwargs['author_identity']; calls.append(identity)
            if identity == 'host.scene-original:v1':
                return HostSceneOriginal(text='Complete independent scene fixture.')
            return HostScreenplayDecision(choice='KEEP_ALL', reason='Whole fixture retained.')
    class Direction:
        async def author(self, request):
            assert request.screenplay_context['screenplay']['text'] == 'Complete independent scene fixture.'
            raise RuntimeError('Controlled failure after preserved V1 and Host decision')
    plugin.creative.canon_author = FormalCanonAuthor(TextOnlyClient(), Path('/missing-skills'))
    plugin.creative.direction_author = Direction()
    run = plugin.create_film_run(work_id='a', mode=RunMode.EXPERIMENT, source=source())
    refs = [plugin.creative.state.input(run.run_id).source_ref]
    c = canon()
    for kind, body in ((Kind.WORK,c.work),(Kind.SCRIPT,c.script),(Kind.SCENE,c.scene)):
        refs.append(plugin.creative_versions.write(writer=Authority.CANON,kind=kind,scope=run.scope,
            body=body,sources=tuple(refs),operation=run.run_id+':'+kind.value))
    plugin.creative.state.save(run.run_id,run.scope,CreativeCheckpoint(refs=tuple(refs)))
    inputs = CapabilityInput(run_id=run.run_id,scope=run.scope,operation_id=run.run_id+':direction')
    for _ in range(2):
        with pytest.raises(RuntimeError, match='Controlled failure'):
            await plugin.creative._direction(inputs)
        cp = plugin.creative.state.checkpoint(run.run_id)
        assert inputs.operation_id not in cp.completed_operations
        assert all(plugin.creative_versions.resolve(r).kind != Kind.SHOT for r in cp.refs)
    assert calls.count('host.scene-original:v1') == 1
    assert cp.screenplay_ref is not None
    assert plugin.screenplays.objects.read_ref(cp.screenplay_ref)['screenplay']['text'] == 'Complete independent scene fixture.'
