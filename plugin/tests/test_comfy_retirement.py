"""No paid traffic is possible through retired live admission paths."""
import pytest
from drama_plugin.config.video_route import VideoRoutePolicy, provider_allowed, require_runtime_route
from drama_plugin.providers.video.registry import model_enabled, model_keys


@pytest.mark.parametrize('provider',['auto','official','comfy_cloud'])
def test_retired_provider_cannot_be_selected_by_any_policy(provider):
    assert not provider_allowed(VideoRoutePolicy(provider=provider),'comfy_cloud')
    with pytest.raises(ValueError,match='COMFY_CLOUD_RETIRED'):
        require_runtime_route('comfy_cloud','minimax-h3',policy=VideoRoutePolicy(provider=provider))


def test_legacy_model_names_remain_readable_but_cannot_be_reenabled():
    assert {'seedance-2.5','flux-3'} <= model_keys()
    assert not model_enabled('seedance-2.5',{'DRAMA_VIDEO_MODEL_SEEDANCE_2_5_ENABLED':'true'})
    assert not model_enabled('flux-3',{'DRAMA_VIDEO_MODEL_FLUX_3_ENABLED':'true'})
    assert model_enabled('minimax-h3',{'DRAMA_VIDEO_MODEL_MINIMAX_H3_ENABLED':'true'})
    assert model_enabled('seedance-2-fast',{'DRAMA_VIDEO_MODEL_SEEDANCE_2_FAST_ENABLED':'true'})


def test_default_image_selector_cannot_fall_back_to_comfy(monkeypatch):
    from drama_plugin.visual.image_route import select_frame_template
    monkeypatch.setattr('drama_plugin.config.production_routes.selected',lambda:{'image_provider':'comfy_cloud'})
    with pytest.raises(ValueError,match='COMFY_CLOUD_RETIRED'):
        select_frame_template(object())


async def test_retired_reserved_image_cannot_claim_or_invoke():
    from drama_plugin.hosts.mcp_execution import invoke_reserved
    class Registry:
        async def discover(self):raise AssertionError('retired discovery')
        async def invoke(self,*args):raise AssertionError('retired paid invocation')
    async def claim(*args):raise AssertionError('must not consume a reservation')
    def verify(*args):raise AssertionError('must reject before live compilation')
    attempt={'status':'RESERVED','job_id':None,'execution_binding':{'execution':{'backend':{'provider':'comfy_cloud'}}}}
    with pytest.raises(ValueError,match='COMFY_CLOUD_RETIRED'):
        await invoke_reserved(attempt,Registry(),verify_request=verify,claim_submission=claim)


@pytest.mark.parametrize('route',['comfy_cloud','comfy-cloud','Comfy','comfy-cloud-mcp'])
def test_native_film_entry_rejects_retired_route_before_any_write(route):
    from drama_plugin.plugin import DramaPlugin
    from drama_plugin.exceptions import ConfigurationError
    # The guard precedes every owner/store access; no initialized Plugin is needed.
    with pytest.raises(ConfigurationError,match='COMFY_CLOUD_RETIRED'):
        DramaPlugin.create_source_film_run(object(),work_id='unwritten',source=None,
            profile=None,rights_refs=(),route=route,model='minimax-h3',run_id='unwritten')
