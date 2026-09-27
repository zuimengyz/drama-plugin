import os
import pytest


@pytest.fixture
def retained_production_policy(monkeypatch):
    """Isolate retained adapter/contract tests from the new deployment selection.

    These suites exercise old Comfy/GPT/other model contracts, not admission of
    those disabled routes today. Current formal policy is tested separately in
    test_fixed_production_routes without this fixture. No production bypass.
    """
    monkeypatch.setattr('drama_plugin.config.production_routes.require_video', lambda *a: None)
    monkeypatch.setattr('drama_plugin.config.production_routes.require_image', lambda *a: None)
    monkeypatch.setattr('drama_plugin.config.production_routes.selected',
                        lambda *a: {'image_provider': 'comfy_cloud'})

@pytest.fixture(autouse=True)
def restore_visual_runtime_environment():
    names = ('DRAMA_PLUGIN_VISUAL_MEDIUM', 'DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT')
    before = {name: os.environ.get(name) for name in names}
    yield
    for name, value in before.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
