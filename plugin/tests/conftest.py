import os
import pytest

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
