"""Route attestations survive age; changed content and financial safety do not."""
from datetime import datetime, timezone
import pytest
from drama_plugin.hosts.http_video import candidate
from drama_plugin.visual.video_selection import Evidence, content_binding_errors, qualify_route
from test_video_selection import fixture, evidence
from test_production_route import route


def official(tmp_path):
    r, c, *_ = fixture(tmp_path)
    return candidate(r, 'seedance-2-fast', cost=c.cost,
                     evidence=Evidence.model_validate(evidence()), quality=c.quality)


def test_age_does_not_change_route_or_cost(tmp_path, retained_production_policy):
    r = route(tmp_path)
    original = r.model_dump(mode='json')
    future = datetime(2199, 1, 1, tzinfo=timezone.utc)
    assert qualify_route(r, now=future)['eligible']
    assert r.candidate.cost.total(future) == r.candidate.cost.total(datetime.now(timezone.utc))
    assert r.model_dump(mode='json') == original
    # Ephemeral balance/quote consumers retain their separate time semantics.
    assert not r.candidate.cost.evidence.current(future)


@pytest.mark.parametrize('field,error', [
    ('adapter_fingerprint', 'INTERFACE_FINGERPRINT_CHANGED'),
    ('graph_hash', 'TEMPLATE_FINGERPRINT_CHANGED'),
    ('variant', 'OFFICIAL_CAPABILITY_CHANGED'),
    ('model', 'OFFICIAL_CAPABILITY_CHANGED'),
])
def test_changed_content_fails(tmp_path, monkeypatch, field, error):
    monkeypatch.setenv('DRAMA_PLUGIN_ROUTE_VIDEO_MODEL', 'seedance-2-fast')
    c = official(tmp_path)
    assert content_binding_errors(c) == []
    assert error in content_binding_errors(c.model_copy(update={field: '0' * 64}))


def test_changed_schema_fingerprint_fails(tmp_path, monkeypatch):
    c = official(tmp_path)
    monkeypatch.setattr('drama_plugin.providers.video.registry.fingerprint', lambda _: '0' * 64)
    errors = content_binding_errors(c)
    assert 'INTERFACE_FINGERPRINT_CHANGED' in errors
    assert 'TEMPLATE_FINGERPRINT_CHANGED' in errors


@pytest.mark.parametrize('key,value', [
    ('DRAMA_PLUGIN_ACTIVE_ROUTE', 'image2_vidu'),
    ('DRAMA_PLUGIN_ROUTE_VIDEO_MODEL', 'seedance-2-standard'),
    ('DRAMA_PLUGIN_ROUTE_IMAGE_MODEL', 'unconfigured'),
])
def test_changed_project_config_fails(tmp_path, monkeypatch, key, value):
    c = official(tmp_path)
    monkeypatch.setenv(key, value)
    assert 'PROJECT_CONFIG_CHANGED' in content_binding_errors(c)


def test_unverified_cost_stays_unresolved(tmp_path, retained_production_policy):
    r = route(tmp_path)
    r = r.model_copy(update={'candidate': r.candidate.model_copy(update={
        'cost': r.candidate.cost.model_copy(update={'evidence': r.candidate.cost.evidence.model_copy(update={'verified': False})})})})
    assert not qualify_route(r)['eligible']


def test_classified_cost_attestations_survive_time(tmp_path, retained_production_policy):
    from test_cost_authority import classified
    from drama_plugin.visual.video_selection import ProductionRoute
    raw = route(tmp_path).model_dump(mode='json')
    raw['candidate']['cost'] = classified(raw['candidate']['cost'])
    assert qualify_route(ProductionRoute.model_validate(raw),
                         now=datetime(2199, 1, 1, tzinfo=timezone.utc))['eligible']


def test_changed_endpoint_config_fails(tmp_path, monkeypatch):
    from drama_plugin.providers.video.registry import ProviderSettings
    c = official(tmp_path)
    monkeypatch.setattr('drama_plugin.providers.video.registry.settings', lambda: {
        'seedance': ProviderSettings(base_url='https://other.example/api/v3', api_key='offline')})
    assert 'OFFICIAL_CONFIG_CHANGED' in content_binding_errors(c)
