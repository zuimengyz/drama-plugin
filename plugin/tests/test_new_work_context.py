"""Cold-start context must not touch existing creative memory."""
import pytest

from drama_plugin.config import load_config
from drama_plugin.context.rhythm import RhythmContextProvider
from drama_plugin.contracts.context import ContextBuildRequest, DramaRunContext
from drama_plugin.exceptions import ContextBuildError


class RecordingProvider:
    def __init__(self):
        self.calls = []

    async def build_context(self, request):
        self.calls.append(request)
        raise ContextBuildError("missing domain")


@pytest.mark.asyncio
async def test_new_work_never_reads_memory_and_projects_config():
    memory = RecordingProvider()
    context = RhythmContextProvider(memory, load_config(environment={'rhythm_speed': 'slow'}))
    request = ContextBuildRequest(scope='WORK', resource_id='fresh-run', purpose='WORK_CREATION',
                                  options={'newWork': True, 'researchContext': {'sourceLock': 'fresh'}})
    result = await context.build_context(request)
    assert not memory.calls
    assert result.work is None and result.script is None and result.episode is None
    assert result.scene is None and result.shot is None
    assert result.creative_rhythm.rhythm_speed == 'slow'
    assert result.research_context == {'sourceLock': 'fresh'}


@pytest.mark.asyncio
@pytest.mark.parametrize('changes', [
    {'scope': 'SCENE'}, {'purpose': 'SHOT_DESIGN'},
    {'options': {'newWork': True, 'creativeRevisionId': 'old'}},
])
async def test_new_work_cannot_resume_or_override_other_scopes(changes):
    memory = RecordingProvider()
    context = RhythmContextProvider(memory, load_config(environment={}))
    args = dict(scope='WORK', resource_id='fresh-run', purpose='WORK_CREATION', options={'newWork': True})
    args.update(changes)
    with pytest.raises(ContextBuildError, match='newWork requires'):
        await context.build_context(ContextBuildRequest(**args))
    assert not memory.calls


@pytest.mark.asyncio
async def test_missing_work_does_not_silently_become_cold_start():
    memory = RecordingProvider()
    context = RhythmContextProvider(memory, load_config(environment={}))
    with pytest.raises(ContextBuildError, match='missing domain'):
        await context.build_context(ContextBuildRequest(scope='WORK', resource_id='unknown', purpose='WORK_CREATION'))
    assert len(memory.calls) == 1
