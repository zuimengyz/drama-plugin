import pytest
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.visual_route import RouteStyleContract
from drama_plugin.hosts.specialized_asset import _check_request_medium
from test_visual_route import context


@pytest.mark.parametrize('authority,route', [('LIVE_ACTION', 'live_action_realist'), ('CG', 'stylized_cinematic_cg')])
@pytest.mark.parametrize('medium', ['PHOTOGRAPHIC', 'DESIGNED_CG', 'DESIGNED_ANIMATION', 'HYBRID', 'PROVIDER_DEFINED'])
def test_typed_and_authority_agree(authority, route, medium):
    style = dump_contract(context(route).style)
    style['medium'] = medium
    valid = medium == ('PHOTOGRAPHIC' if authority == 'LIVE_ACTION' else 'DESIGNED_CG')
    if valid:
        RouteStyleContract.model_validate(style)
        _check_request_medium(authority, style)
    else:
        with pytest.raises(ValueError, match='VISUAL_ROUTE_MEDIUM_MISMATCH'):
            RouteStyleContract.model_validate(style)
        with pytest.raises(ValueError, match='MOVIE_MEDIUM_OVERRIDE_FORBIDDEN'):
            _check_request_medium(authority, style)


@pytest.mark.parametrize('alias', ['LIVE_ACTION', 'LIVE_ACTION_PHOTOREAL', 'live_action_realist', 'PHOTOGRAPHIC'])
def test_live_aliases(alias):
    _check_request_medium('LIVE_ACTION', {'nested': [{'medium': alias}]})
    with pytest.raises(ValueError, match='MOVIE_MEDIUM_OVERRIDE_FORBIDDEN'):
        _check_request_medium('CG', {'medium': alias})


@pytest.mark.parametrize('alias', ['CG', 'CINEMATIC_CG', 'DESIGNED_CG', 'stylized_cinematic_cg'])
def test_cg_aliases(alias):
    _check_request_medium('CG', {'medium': alias})
    with pytest.raises(ValueError, match='MOVIE_MEDIUM_OVERRIDE_FORBIDDEN'):
        _check_request_medium('LIVE_ACTION', {'medium': alias})


@pytest.mark.parametrize('value', ['stylized_animation', 'DESIGNED_ANIMATION', 'animation', 'unrelated', None, {}])
def test_unrelated_tokens_rejected(value):
    with pytest.raises(ValueError, match='MOVIE_MEDIUM_OVERRIDE_FORBIDDEN'):
        _check_request_medium('LIVE_ACTION', {'medium': value})


def test_other_guards_preserved():
    with pytest.raises(ValueError, match='PROVIDER_ENHANCEMENT_NOT_AUTHORIZED'):
        _check_request_medium('LIVE_ACTION', {'promptEnhancement': True})
    with pytest.raises(ValueError, match='MOVIE_MEDIUM_OVERRIDE_FORBIDDEN'):
        _check_request_medium('LIVE_ACTION', {'rendering': 'CG character'})
