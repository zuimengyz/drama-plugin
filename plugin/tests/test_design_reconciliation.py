"""Generic contract/gate regressions: no media, story fixtures or entity matching."""
from copy import deepcopy
import pytest
from pydantic import ValidationError
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.location_design import LocationDesign, LocationDesignRef, SceneLocationBinding, SceneLocationOverride
from drama_plugin.contracts.character_evidence import CharacterEvidence, CharacterCoverageReview
from drama_plugin.contracts.production_design import CharacterVisualSpec, ProductionDesignContent
from drama_plugin.contracts.preproduction import FilmProductionDesign, SceneProductionDesignPacket
from drama_plugin.production_design import resolve_location_design, review_character_coverage
from drama_plugin.preproduction import department_integration
from drama_plugin.director import pin
from preproduction_helpers import make_case


def basis(scope='DESIGN', scene=None):
    return dict(source_ref='source:bounded-excerpt', claim='Specific supported claim',
                scope=scope, scene_ref=scene, evidence_status='DOCUMENTED', limitation='Only the cited action or identity')


def location(kind='riverbank', scenes=('war1', 'war2', 'war3'), identity='ENV-1'):
    values = {k: 'Explicit authored spatial constraint' for k in (
        'dramatic_function', 'macro_geography', 'terrain', 'ground_condition',
        'architecture_or_structures', 'fortification_or_boundary', 'scale_and_density',
        'human_activity', 'surface_texture', 'time_of_day', 'weather', 'lighting_behavior',
        'color_environment', 'acoustic_character')}
    values.update(id=identity, name='Shared landing', revision='r1', location_type=kind,
        scene_refs=scenes, historical_basis=[basis()], evidence_status='DRAMATIC_RECONSTRUCTION',
        uncertainties=['Exact historical dimensions unknown'], zone_layout={'A':'shore', 'B':'ramp', 'C':'boat'},
        landmarks={'post':'fixed ramp post'}, entrances=['A'], exits=['C'], movement_routes={'boarding':['A','B','C']},
        line_of_sight=['Post and boat remain mutually visible'], materials=['wood', 'earth'],
        prop_families=['boat tackle'], light_sources=['sky'], camera_affordances=['Shore-side angle keeps ramp visible'],
        blocking_affordances=['One person clears ramp before next arrives'], action_constraints=['No instant boat reset'],
        sound_sources=['water'], continuity_anchors=['Post remains landward'],
        phase_ii_visual_requirements=['Later prove ramp clearance; design only now'], forbidden_assumptions=['No invented monumental buildings'])
    return LocationDesign(**values)


def evidence(status='DRAMATIC_RECONSTRUCTION', scenes=('war1',), roles=('witness',)):
    documented = status == 'DOCUMENTED'
    return dict(historical_status=status, identity_kind='HISTORICAL_PERSON' if documented else 'ORIGINAL',
        historical_authority=documented, source_basis=[basis('IDENTITY')] if documented else [],
        dramatic_function=roles, fictionalization_boundary='Private words are authored, no historical authority inferred',
        scene_refs=scenes, scene_placements=[dict(scene_id=s, evidence_status=status,
            source_basis=[basis('SCENE_PLACEMENT', s)] if documented else [],
            fictionalization_boundary='Only the scoped presence is supported') for s in scenes])


def character(identity='original-person', status='DRAMATIC_RECONSTRUCTION', scenes=('war1',), roles=('witness',)):
    return CharacterVisualSpec(character_identity=identity, revision='r1', dramatic_role='Bystander',
        visual_objective='Readable ordinary presence', silhouette='Working clothes', evidence=evidence(status, scenes, roles))


def coverage(identity='documented-person', decision='INCLUDE'):
    return CharacterCoverageReview(scene_refs=['war1'], inventory_basis='Review cited scene action, no headcount requirement',
        documented_scene_actors=[dict(character_identity=identity, scene_id='war1', historical_action='Commands the recorded movement',
            source_basis=[basis('SCENE_PLACEMENT', 'war1')])],
        decisions=[dict(character_identity=identity, scene_id='war1', decision=decision, reason='Makes the spatial cause legible')])


def test_legacy_wire_and_fingerprints_are_unchanged():
    _, _, _, artifacts = make_case()
    assert sha256_canonical(artifacts['war:film-design']) == 'e203a750563a0066d33e20f63a7fc7d16a15cc87bcc8f2c48ae880806e52fb8a'
    assert sha256_canonical(artifacts['war:war1-design']) == '2405ee4fcdb2b3f1a48cb77b507716b72295a2be6cebc5591f412557b5ece15a'
    for key, model in [('war:film-design', FilmProductionDesign), ('war:war1-design', SceneProductionDesignPacket), ('war:character-visual', CharacterVisualSpec)]:
        assert dump_contract(model.model_validate(artifacts[key])) == artifacts[key]


@pytest.mark.parametrize('kind', ['camp','tent','palace','hall','city','street','village','fortification','battlefield','mountain','forest','wetland','riverbank','crossing','road','interior','future-orbital-habitat'])
def test_open_location_type_is_carried_not_inferred(kind):
    place = location(kind)
    assert place.location_type == kind
    assert dump_contract(place)['name'] == 'Shared landing'


def test_same_location_two_scenes_and_typed_delta_preserve_base():
    place = location(); raw = dump_contract(place); ref = LocationDesignRef(location_id=place.id, artifact_ref=pin('place:one', place))
    current={ref.artifact_ref.key:ref.artifact_ref.fingerprint}; artifacts={ref.artifact_ref.key:raw}
    for sid in ['war1','war2']:
        use=SceneLocationBinding(location_ref=ref, local_override=SceneLocationOverride(
            ground_change='Ramp is wet', change_reason='Rain between scenes', continuity_note='Post remains fixed'))
        out=resolve_location_design(use, scene_id=sid,current=current,artifacts=artifacts)
        assert out['base'] == raw and out['localOverride']['groundChange']=='Ramp is wet'
        assert out['productionAuthorized'] is False
    assert artifacts[ref.artifact_ref.key] == raw
    with pytest.raises(ValidationError):
        SceneLocationOverride(zone_layout={'X':'replacement scene'}, change_reason='Convenience', continuity_note='reset')


@pytest.mark.parametrize('failure', ['stale', 'identity', 'scope', 'mutated'])
def test_location_resolution_rejects_unbound_original(failure):
    place=location(); ref=LocationDesignRef(location_id=place.id,artifact_ref=pin('place:one',place))
    current={ref.artifact_ref.key:ref.artifact_ref.fingerprint}; artifacts={ref.artifact_ref.key:dump_contract(place)}
    sid='war1'
    if failure=='stale':current[ref.artifact_ref.key]='0'*64
    if failure=='identity':ref=ref.model_copy(update={'location_id':'OTHER'})
    if failure=='scope':sid='unrelated-scene'
    if failure=='mutated':artifacts[ref.artifact_ref.key]['terrain']='Changed after pin'
    with pytest.raises(ValueError):resolve_location_design(SceneLocationBinding(location_ref=ref),scene_id=sid,current=current,artifacts=artifacts)


def test_documented_identity_does_not_prove_scene_presence():
    raw=evidence('DOCUMENTED'); raw['scene_placements'][0]['source_basis']=[]
    with pytest.raises(ValidationError):CharacterEvidence.model_validate(raw)
    raw=evidence('DOCUMENTED');raw['scene_placements'][0]['source_basis'][0]['scene_ref']='other-scene'
    with pytest.raises(ValidationError):CharacterEvidence.model_validate(raw)


def test_original_same_display_label_never_matches_documented_identity():
    # Explicit identities are opaque strings; similarity confers nothing.
    original=character(identity='documented-person')
    result=review_character_coverage(coverage(),(original,))
    assert result['status']=='CHARACTER_COVERAGE_NOT_READY'
    assert original.evidence.historical_status=='DRAMATIC_RECONSTRUCTION'
    assert not original.evidence.historical_authority
    raw=evidence();raw['historical_authority']=True
    with pytest.raises(ValidationError):CharacterEvidence.model_validate(raw)
    raw=evidence();raw['historical_status']='DOCUMENTED';raw['source_basis']=[basis('IDENTITY')]
    with pytest.raises(ValidationError):CharacterEvidence.model_validate(raw)


def test_explicit_coverage_can_include_or_exclude_without_count_kpi():
    assert review_character_coverage(coverage(),(character('documented-person','DOCUMENTED'),))['status']=='CHARACTER_COVERAGE_READY'
    assert review_character_coverage(coverage(decision='EXCLUDE_WITH_REASON'),())['status']=='CHARACTER_COVERAGE_READY'
    empty=CharacterCoverageReview(scene_refs=['war1'],documented_scene_actors=[], decisions=[],inventory_basis='This scene has no documented named actor')
    assert review_character_coverage(empty,())['status']=='CHARACTER_COVERAGE_READY'
    raw=dump_contract(coverage());raw['decisions']=[]
    with pytest.raises(ValidationError):CharacterCoverageReview.model_validate(raw)


def test_fictional_proxy_overload_is_note_not_blocker():
    review=CharacterCoverageReview(scene_refs=['war1'],documented_scene_actors=[],decisions=[],inventory_basis='Fictional witness assessment')
    c=character(roles=('tactical explanation','historical information','emotional proxy','audience view','moral commentary','relationship','intelligence','casualty feedback'))
    result=review_character_coverage(review,(c,))
    assert result['status']=='CHARACTER_COVERAGE_READY' and result['missing']==[]
    assert result['notes'][0]['code']=='FICTIONAL_PROXY_OVERLOAD' and result['notes'][0]['severity']=='NOTE'


def with_reusable_places(include_characters=False):
    packet,review,current,artifacts=make_case()
    def keep(key,value):
        raw=dump_contract(value) if hasattr(value,'model_dump') else value
        ref=pin(key,raw);current[key]=ref.fingerprint;artifacts[key]=raw
        return ref
    place=location();ref=LocationDesignRef(location_id=place.id,artifact_ref=keep('place:shared',place))
    film=deepcopy(artifacts['war:film-design']);film['locationDesignRefs']=[dump_contract(ref)]
    if include_characters:
        film['characterVisualRefs']=[dump_contract(keep('character:'+identity, character(identity, scenes=packet.scene_ids))) for identity in ('war-lead','war-other')]
        review_value=CharacterCoverageReview(scene_refs=packet.scene_ids,documented_scene_actors=[],decisions=[],inventory_basis='Entirely fictional generic fixture')
        film['characterCoverageRef']=dump_contract(keep('character:coverage',review_value))
    film_ref=keep('war:film-design',FilmProductionDesign.model_validate(film))
    changes={'war:film-design':film_ref}
    for sid in packet.scene_ids:
        scene=deepcopy(artifacts['war:'+sid+'-design']);scene.pop('location')
        scene['filmDesignRef']=dump_contract(film_ref)
        scene['environmentRefs']=[dump_contract(SceneLocationBinding(location_ref=ref))]
        scene_ref=keep('war:'+sid+'-design',SceneProductionDesignPacket.model_validate(scene));changes[scene_ref.key]=scene_ref
        light=deepcopy(artifacts['war:'+sid+'-light']);light['sceneDesignRef']=dump_contract(scene_ref)
        light_ref=keep('war:'+sid+'-light',light);changes[light_ref.key]=light_ref
    entries=tuple(e.model_copy(update={'artifact_ref':changes.get(e.artifact_ref.key,e.artifact_ref)}) for e in packet.entries)
    sr=deepcopy(artifacts[packet.self_review_ref.key]);sr['reviewedArtifacts']=[[e.artifact_ref.key,e.artifact_ref.fingerprint] for e in entries]+[[r.key,r.fingerprint] for r in packet.sequence_transition_refs]
    packet=packet.model_copy(update={'entries':entries,'self_review_ref':keep(packet.self_review_ref.key,sr)})
    return packet,review,current,artifacts


def test_existing_director_gate_consumes_shared_environment_without_media():
    p,r,c,a=with_reusable_places()
    result=department_integration(p,r,c,a)
    assert result['status']=='DEPARTMENT_REVIEW_READY' and result['productionAuthorized'] is False
    assert len([key for key in a if key.startswith('place:')])==1


def test_scene_cannot_mix_old_copy_and_new_location_reference():
    _,_,_,a=make_case();raw=deepcopy(a['war:war1-design'])
    place=location();raw['environmentRefs']=[dump_contract(SceneLocationBinding(location_ref=LocationDesignRef(location_id=place.id,artifact_ref=pin('place:shared',place))))]
    with pytest.raises(ValidationError):SceneProductionDesignPacket.model_validate(raw)


def test_reusable_location_uses_existing_design_handoff_owner():
    from drama_plugin.production_design import design_handoff, verify_design_handoff
    value=ProductionDesignContent(creative_kind='LOCATION_DESIGN',semantic_key='production-design/location/shared-r1',
        title='Shared environment candidate',spec=location(),provenance={'source_type':'PROJECT','source_note':'Existing screenplay revision'},
        validation={'status':'PROJECT_DERIVED'},stable_reuse_reason='One place is reused across three scenes')
    out=design_handoff(value,consumer='shot-design')
    assert isinstance(verify_design_handoff(out).spec,LocationDesign)
    assert out['productionEligible'] is False
    assert out['content']['spec']['locationType']=='riverbank'
    with pytest.raises(ValueError):design_handoff(value,consumer='shot-design',for_production=True)


def test_missing_required_spatial_capability_or_unknown_zone_fails():
    raw=dump_contract(location());raw.pop('cameraAffordances')
    with pytest.raises(ValidationError):LocationDesign.model_validate(raw)
    raw=dump_contract(location());raw['movementRoutes']['impossible']=['A','undeclared']
    with pytest.raises(ValidationError):LocationDesign.model_validate(raw)


def test_live_gate_rejects_stale_shared_environment():
    p,r,c,a=with_reusable_places();a['place:shared']['terrain']='Repinned elsewhere without updating this film'
    with pytest.raises(ValueError,match='stale department original'):department_integration(p,r,c,a)


def test_existing_gate_consumes_explicit_character_evidence_inventory():
    p,r,c,a=with_reusable_places(include_characters=True)
    result=department_integration(p,r,c,a)
    assert result['status']=='DEPARTMENT_REVIEW_READY'
    assert result['productionAuthorized'] is False
