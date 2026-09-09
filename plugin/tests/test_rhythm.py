"""Narrative configuration reaches the public creation tool and survives resume."""
import json
import os
from pathlib import Path
import subprocess

import pytest

from drama_plugin import ContextBuildRequest, DramaPlugin
from drama_plugin.config import load_config
from drama_plugin.exceptions import ConfigurationError, ContextBuildError
from drama_plugin.providers.mock import MockMemoryProvider

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]

@pytest.mark.parametrize(('value', 'expected'), [(None, 'medium'), ('medium', 'medium'), (' fast \t', 'fast')])
def test_config_rhythm(value, expected):
    config = load_config(environment={} if value is None else {'rhythm_speed': value})
    assert config.rhythm_speed == expected
    assert config.rhythm_source == ('default:medium' if value is None else 'environment:rhythm_speed')

@pytest.mark.parametrize('value', ['', ' ', 'FAST', 'slow', '1'])
def test_invalid_rhythm_identifies_key_and_source(value):
    with pytest.raises(ConfigurationError, match='rhythm_speed in environment'):
        load_config(environment={'rhythm_speed': value})


def test_yaml_rhythm_trim_override_and_error(tmp_path):
    path = tmp_path / 'config.yaml'
    path.write_text('rhythm_speed: " fast "\n')
    config = load_config(path, environment={})
    assert config.rhythm_speed == 'fast' and str(path) in config.rhythm_source
    assert load_config(path, {'rhythm_speed': 'medium'}).rhythm_speed == 'medium'
    path.write_text('rhythm_speed: null\n')
    with pytest.raises(ConfigurationError, match='rhythm_speed in configuration'):
        load_config(path, {})

@pytest.mark.asyncio
async def test_actual_tool_new_revision_resume_and_refresh(monkeypatch):
    request = ContextBuildRequest(scope='EPISODE', resource_id='episode-1', purpose='SHOT_DESIGN')
    monkeypatch.setenv('rhythm_speed', 'medium')
    async with DramaPlugin.load(ROOT) as first:
        saved = await first.tools.invoke('context.build_context', request=request)
        assert saved.creative_rhythm.rhythm_speed == 'medium'
        profile = saved.creative_rhythm.model_dump(by_alias=True)
    monkeypatch.setenv('rhythm_speed', 'fast')
    async with DramaPlugin.load(ROOT) as second:
        memory = second.providers.memory
        assert isinstance(memory, MockMemoryProvider)
        memory.data.work = memory.data.work.model_copy(update={'content': {
            **memory.data.work.content, 'creativeRevisions': {'old': {'rhythm': profile}}
        }})
        new = await second.tools.invoke('context.build_context', request=request)
        assert new.creative_rhythm.rhythm_speed == 'fast'
        assert '并行' in new.creative_rhythm.semantics
        resumed_request = request.model_copy(update={'options': {'creativeRevisionId': 'old'}})
        resumed = await second.tools.invoke('context.build_context', request=resumed_request)
        assert resumed.creative_rhythm.model_dump(by_alias=True) == profile
        patch = await second.context.refresh(request, saved)
        assert not any(x.path == '/creativeRhythm' for x in patch.changes)
        assert (await second.context.build(request)).creative_rhythm == new.creative_rhythm
        with pytest.raises(ContextBuildError, match='Saved creativeRevisionId'):
            await second.tools.invoke('context.build_context', request=request.model_copy(update={'options': {'creativeRevisionId': 'missing'}}))

@pytest.mark.parametrize('shell', ['bash', 'zsh'])
def test_source_export_exec_reaches_public_tool(tmp_path, shell):
    import sys
    env_file = tmp_path / 'plugin.env'
    env_file.write_text('rhythm_speed=" fast "\n')
    child = tmp_path / 'child.py'
    child.write_text('''import asyncio, json
from drama_plugin import DramaPlugin, ContextBuildRequest
async def main():
 async with DramaPlugin.load() as p:
  c = await p.tools.invoke("context.build_context", request=ContextBuildRequest(scope="EPISODE",resource_id="episode-1",purpose="SHOT_DESIGN"))
  print(json.dumps(c.creative_rhythm.model_dump(by_alias=True)))
asyncio.run(main())
''')
    environment = {k:v for k,v in os.environ.items() if not k.startswith('DRAMA_PLUGIN_') and k != 'rhythm_speed'}
    environment['PYTHONPATH'] = str(ROOT / 'src')
    result = subprocess.run([shell, '-c', 'source "$1" "$2"; exec "$3" "$4"', 'rhythm-test', str(WORKSPACE / 'scripts/load-env.sh'), str(env_file), sys.executable, str(child)], env=environment, capture_output=True, text=True, check=True)
    profile = json.loads(result.stdout)
    assert profile['rhythm_speed'] == 'fast'
    assert profile['source'] == 'environment:rhythm_speed'
    assert '并行' in profile['semantics']


def test_rhythm_belongs_only_to_plugin(tmp_path):
    import runpy
    ownership = runpy.run_path(str(WORKSPACE / 'scripts/runtime-env-ownership.py'))
    env_file = tmp_path / 'component.env'
    env_file.write_text('rhythm_speed=medium\n')
    assert ownership['validate']('drama-plugin', env_file) == ['rhythm_speed']
    for owner in ['mcp-host', 'drama-service']:
        with pytest.raises(ValueError, match='not owned by component: rhythm_speed'):
            ownership['validate'](owner, env_file)
