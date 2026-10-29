from pathlib import Path
from drama_plugin.creative_engine.screenplay import ScreenplayWorkshop, ContextOriginal
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
from drama_plugin.creative_engine.backends import FormalDirectionAuthor, HostSceneOriginal
from drama_plugin.creative_engine.author_projection import screenplay_view


def test_project_author_context_survives_selection(tmp_path):
    w = ScreenplayWorkshop(DirectorArtifactStore(tmp_path))
    source = w.retain_context(ContextOriginal(work_id='film', label='source', status='DESIGNATED_SOURCE', text='Source text'))
    context = {'adaptationAuthority': 'May restructure scenes', 'creativePreferences': 'Natural speech',
               'professionalGuidance': [{'status': 'ADVISORY', 'text': 'Contact may release'}]}
    packet = w.begin(session_id='film-v4', work_id='film', scope='FILM', goal='Write anew', source_refs=(source,), author_context=context)
    assert packet['authorPacket']['authorContext'] == context
    w.retain_v1('film-v4', 'Complete original')
    w.decide('film-v4', choice='KEEP_ALL', reason='Selected', expected_revision=1)
    projected = screenplay_view(w.selected_packet('film-v4'))
    assert projected['context']['authorContext'] == context
    assert projected['screenplay']['text'] == 'Complete original'
    assert projected['formalAdoptionRequired'] is True


async def test_director_treatment_receives_full_body_and_project_context():
    class Client:
        async def complete(self, role, system, request, result, **kwargs):
            assert role == 'direction'
            assert 'proposed screenplay changes' in system.lower() or 'proposed writer changes' in system.lower()
            assert kwargs['model_payload'] == packet
            assert kwargs['author_identity'] == 'film.director-treatment:v2'
            return HostSceneOriginal(text='Full treatment with proposed feedback')
    packet = {'screenplay': 'Scene 1 ... Scene 9 ending', 'authorContext': {'userFeedback': 'New structure allowed'}}
    author = FormalDirectionAuthor(Client(), Path(__file__).resolve().parents[1] / 'skills')
    result = await author.film_treatment(None, packet)
    assert result.text == 'Full treatment with proposed feedback'

from test_host_first_screenplay import plugin

async def test_registered_begin_tool_delivers_project_context(plugin):
    source = await plugin.tools.invoke('screenplay.retain_context', original=ContextOriginal(
        work_id='film', label='source', status='DESIGNATED_SOURCE', text='Whole literary source'))
    packet = await plugin.tools.invoke('screenplay.begin', session_id='tool-context', work_id='film',
        scope='FILM', goal='Recreate', source_refs=(source,),
        author_context={'adaptationAuthority': {'restructure': True}, 'creativePreferences': '6:4, not seconds'})
    assert packet['authorPacket']['authorContext']['adaptationAuthority']['restructure'] is True


async def test_native_film_writer_and_revision_receive_project_context(tmp_path):
    from types import SimpleNamespace
    from drama_plugin.creative_engine.screenplay_author import native_film_original
    from drama_plugin.creative_engine.contracts import SourceBody
    class Author:
        async def film_original(self, request, packet):
            assert packet['authorContext'] == context
            return HostSceneOriginal(text='Complete beginning to ending')
        async def scene_decision(self, request, packet):
            assert packet['authorContext'] == context
            assert packet['preservedV1']['text'] == 'Complete beginning to ending'
            return SimpleNamespace(choice='KEEP_ALL', reason='Coherent whole film', text=None)
    context = {'adaptationAuthority': 'May reorder', 'professionalGuidance': ['Weight transfer'],
               'directorFeedback': {'status': 'ADVISORY', 'text': 'Consider an earlier interruption'}}
    request = SimpleNamespace(screenplay_context={'authorContext': context},
        scope=SimpleNamespace(work_id='film'),
        source=SourceBody(goal='Complete film', text='Designated source', spoken_language='ru'))
    workshop = ScreenplayWorkshop(DirectorArtifactStore(tmp_path))
    selected = await native_film_original(workshop, Author(), request, operation='context-flow')
    assert selected['context']['authorContext'] == context
    assert selected['formalAdoptionRequired'] is True
