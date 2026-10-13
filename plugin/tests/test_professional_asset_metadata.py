"""Owner-injected Asset originals are provenance, not Professional re-authorship."""
from copy import deepcopy

import pytest
from pydantic import ValidationError

from drama_plugin.contracts.base import canonical_json, dump_contract, sha256_canonical
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.creative_engine.contracts import AuthorRequest, DesignBody, SourceBody
from drama_plugin.creative_engine.store import CreativeVersionStore
from drama_plugin.professional_design.provenance import reject_model_metadata
from drama_plugin.professional_design.resolver import ProfessionalDesignResolver
from drama_plugin.runtime.contracts import RuntimeScope


@pytest.mark.parametrize('domain', ['SUBJECTS', 'WORLD', 'REFERENCE'])
def test_real_resolver_persist_and_reopened_owner_preserve_complete_asset(domain, tmp_path):
    versions = CreativeVersionStore(tmp_path / 'originals')
    original = {
        'geometry': 'One small tapered wooden body and its matching sole lid',
        'interpretation': 'Dimensions and marks are approved art choices, not source facts',
        'purpose': 'Reusable construction identity for the same object',
    }
    design_pin = versions.objects.put('approved-prop-design', original)
    adoption_pin = versions.objects.put('approved-prop-adoption', {
        'decision': 'ADOPT', 'designRef': dump_contract(design_pin),
        'referenceMediaIds': ['reviewed-prop-image'],
    })
    narrative_pin = versions.objects.put('selected-asset-narrative', {'workId': 'work'})
    binding = {
        'id': 'prop-asset', 'workId': 'work', 'assetType': 'PROP',
        'referenceMediaIds': ['reviewed-prop-image'],
        'content': {'specializedAsset': {
            'state': 'ADOPTED', 'stableIdentity': 'same-prop', 'revision': 1,
            'design': deepcopy(original), 'designRef': dump_contract(design_pin),
            'adoptionRef': dump_contract(adoption_pin),
        }},
    }
    expected = deepcopy(binding)
    original_bytes = canonical_json(original)
    expected_binding_bytes = canonical_json(expected)
    request = AuthorRequest(scope=RuntimeScope(work_id='work', scene_id='scene', shot_id='shot'),
        source=SourceBody(goal='Test retained owner metadata', text='A person carries the small object.',
            spoken_language='en'),
        source_refs=(), professional_context={'assetSequence': {
            'narrativeRef': dump_contract(narrative_pin), 'currentAssets': [binding],
            'currentTextDesigns': [],
        }})
    authored = DesignBody(domain=domain, facts={'visibleFact': 'Current source-bound action'})
    reject_model_metadata(authored.facts)
    resolver = ProfessionalDesignResolver(None)
    reference = resolver.persist(versions, request, authored, operation='persist-owned-asset:' + domain)
    # Reopen the actual immutable owner to exercise serialized contract
    # validation, rather than checking only a permissive model_copy in memory.
    reopened = CreativeVersionStore(tmp_path / 'originals')
    retained = reopened.resolve(reference).body
    assert canonical_json(retained.facts['assetBindings'][0]) == expected_binding_bytes
    saved_pin = SourcePin.model_validate(retained.facts['assetBindings'][0]['content']['specializedAsset']['designRef'])
    assert saved_pin == design_pin and saved_pin.fingerprint == sha256_canonical(original)
    assert canonical_json(reopened.objects.read_ref(saved_pin)) == original_bytes
    assert retained.facts['assetNarrativeRef'] == dump_contract(narrative_pin)
    assert resolver.asset_inheritance_current(request, (retained,))
    assert binding == expected and authored.facts == {'visibleFact': 'Current source-bound action'}


@pytest.mark.parametrize('facts', [
    {'assetBindings': [{'content': 'Invented owner metadata'}]},
    {'ordinaryCreativeFact': {'assetBindings': [{'content': 'Hidden owner metadata'}]}},
    {'ordinaryCreativeFact': [{'assetBindings': []}]},
])
def test_author_cannot_supply_root_or_nested_binding_metadata(facts):
    with pytest.raises(ValueError, match='PROFESSIONAL_SYSTEM_METADATA_MODEL_OWNERSHIP'):
        reject_model_metadata(facts)


@pytest.mark.parametrize('key', ['interpretation', 'purpose', 'scene_text', 'screenplay', 'dialogue'])
@pytest.mark.parametrize('wrap', [lambda value: value, lambda value: {'ordinaryCreativeFact': [value]}])
def test_ordinary_professional_prose_keeps_recursive_authority_boundary(key, wrap):
    with pytest.raises(ValidationError, match='Professional field authority violation'):
        DesignBody(domain='WORLD', facts=wrap({key: 'An unauthorized new canonical choice'}))


@pytest.mark.parametrize('domain', ['ACTION', 'CAMERA', 'PERFORMANCE', 'SOUND', 'LIGHTING', 'COLOR', 'EDITORIAL'])
def test_other_domains_get_no_system_binding_exception(domain):
    with pytest.raises(ValidationError, match='Professional field authority violation'):
        DesignBody(domain=domain, facts={'assetBindings': [{'design': {'interpretation': 'Stored prose'}}]})


def test_nested_asset_binding_name_does_not_hide_new_artistic_authority():
    with pytest.raises(ValidationError, match='Professional field authority violation'):
        DesignBody(domain='WORLD', facts={'nested': {
            'assetBindings': [{'design': {'interpretation': 'Unauthorized new story'}}],
        }})


def test_system_binding_exception_does_not_hide_sibling_story_rewrite():
    with pytest.raises(ValidationError, match='Professional field authority violation'):
        DesignBody(domain='WORLD', facts={
            'assetBindings': [{'design': {'interpretation': 'Retained owner prose'}}],
            'currentAction': {'purpose': 'Unauthorized Shot intent'},
        })
