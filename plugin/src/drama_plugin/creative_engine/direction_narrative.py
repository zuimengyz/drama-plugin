"""Selected Director prose inside existing creative capabilities, before coverage.

Text packets are pure and usable without a Work or store. Native selections use
ScreenplayWorkshop's existing immutable objects; no Canon writes or adoption.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, TYPE_CHECKING

from drama_plugin.film.contracts import FilmCanon
if TYPE_CHECKING:
    from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
    from drama_plugin.creative_engine.screenplay import ScreenplayWorkshop
    from drama_plugin.creative_engine.backends import FormalDirectionAuthor
    from drama_plugin.creative_engine.contracts import AuthorRequest
    from drama_plugin.film.contracts import FilmAuthorRequest

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.source_pin import SourcePin

SCHEMA = 'director-narrative-original-v1'


def film_packet(screenplay: str, *, source: str, author_context: dict[str, Any] | None = None,
                film_identity: dict[str, Any] | None = None, film_look: list | None = None) -> dict[str, Any]:
    return {'screenplay': screenplay, 'designatedSource': source,
            **({'filmIdentity': film_identity} if film_identity else {}),
            **({'filmLook': film_look} if film_look else {}),
            'authorContext': author_context or {}, 'use': 'DIRECTOR_CANDIDATE_NOT_CANON'}


def scene_packet(screenplay: str, *, film_screenplay: str, film_direction: str,
                 neighbors: list[dict[str, Any]] | tuple[()] = (), author_context: dict[str, Any] | None = None,
                 film_identity: dict[str, Any] | None = None, film_look: list | None = None) -> dict[str, Any]:
    return {'screenplay': screenplay, 'filmScreenplay': film_screenplay,
            **({'filmIdentity': film_identity} if film_identity else {}),
            **({'filmLook': film_look} if film_look else {}),
            'selectedFilmDirection': film_direction, 'neighboringScreenplays': list(neighbors),
            'authorContext': author_context or {}, 'use': 'CURRENT_SCENE_DIRECTION_NOT_SHOT_LIST'}


def selected_view(context: dict[str, Any], scene_id: str | None = None) -> dict[str, Any]:
    """Keep film intent plus only the requested scene; old coverage is separate."""
    value: dict[str, Any] = deepcopy(context.get('directorNarrative', {}))
    if value and scene_id is not None:
        value['scenes'] = {k: v for k, v in value.get('scenes', {}).items() if k == scene_id}
    return value


def retain_selection(objects: DirectorArtifactStore, *, work_id: str, scene_id: str | None,
                     text: str, basis: dict[str, Any], selected_by: str, reason: str,
                     source_refs: list[dict[str, Any]] | tuple[()] = (),
                     authorship: dict[str, Any] | None = None) -> dict[str, Any]:
    if not text.strip() or not reason.strip() or selected_by not in {'HOST', 'DIRECTOR_AUTHOR_CANDIDATE'}:
        raise ValueError('Director selection needs text, reason and explicit authority')
    original = {'schemaVersion': SCHEMA, 'workId': work_id, 'sceneId': scene_id,
        'role': 'SCENE_DIRECTION' if scene_id else 'FILM_NARRATIVE', 'version': 1,
        'text': text, 'basis': basis, 'selectedBy': selected_by, 'selectionReason': reason,
        'formalAdoption': False, 'sourceRefs': list(source_refs), **(authorship or {})}
    ref = objects.put('director-narrative:' + (scene_id or work_id), original)
    return {'ref': dump_contract(ref), **original}


def verify_selection(objects: DirectorArtifactStore, selected: dict[str, Any], *, work_id: str, scene_id: str | None,
                     basis: dict[str, Any] | None = None) -> dict[str, Any]:
    original = objects.read_ref(SourcePin.model_validate(selected['ref']))
    if (original != {k: v for k, v in selected.items() if k != 'ref'}
            or original.get('schemaVersion') != SCHEMA or original.get('workId') != work_id
            or original.get('sceneId') != scene_id
            or original.get('role') != ('SCENE_DIRECTION' if scene_id else 'FILM_NARRATIVE')):
        raise ValueError('Director narrative original or scope mismatch')
    if basis is not None and original['basis'] != basis:
        raise ValueError('Selected director narrative basis changed; return to its author')
    return selected


def screenplay_material(request: AuthorRequest | FilmAuthorRequest) -> tuple[str, list[tuple[str, str]], dict[str, Any]]:
    """Read exact selected writer prose; never reinterpret or mutate Canon."""
    context: dict[str, Any] = dict(request.screenplay_context or {})
    canon = request.canon
    assert canon is not None
    film = canon.script.screenplay
    body = context.get('screenplay', {})
    if body.get('scope') == 'FILM':
        film = body['text']
    scenes = ([(s.scene_id, s.scene.scene_text) for s in canon.scenes]
              if isinstance(canon, FilmCanon) else [(request.scope.scene_id or body.get('sceneId') or request.scope.work_id + ':scene', canon.scene.scene_text)])
    chosen = {s['screenplay']['sceneId']: s['screenplay']['text']
              for s in context.get('selectedSceneScreenplays', ())}
    if body.get('scope') == 'SCENE':
        chosen[body['sceneId']] = body['text']
    scenes = [(sid, chosen.get(sid, text)) for sid, text in scenes]
    author_context: dict[str, Any] = context.get('authorContext', context.get('context', {}).get('authorContext', {}))
    return film, scenes, author_context


async def native_director_narrative(workshop: ScreenplayWorkshop, author: FormalDirectionAuthor,
                                    request: AuthorRequest | FilmAuthorRequest, *, operation: str) -> dict[str, Any]:
    """Called only on an uncached new coverage path. Existing Shots never enter.

    Host mode uses an explicitly selected Host original; MODEL mode retains its
    Director candidate without impersonating Host. Adoption stays downstream.
    """
    context: dict[str, Any] = deepcopy(dict(request.screenplay_context or {}))
    film, scenes, author_context = screenplay_material(request)
    incoming = selected_view(context)
    objects = workshop.objects
    work = request.scope.work_id
    source = request.source.text or request.source.external_reference or request.source.goal
    source_refs: list[dict[str, Any]] = [context[k] for k in ('screenplayRef',) if context.get(k)]
    source_refs += [dump_contract(r) for r in getattr(request, 'source_refs', ())]
    film_source = getattr(request, 'source_ref', None)
    if film_source is not None:
        source_refs.append(dump_contract(film_source))

    async def choose(scene_id: str | None, basis: dict[str, Any], packet: dict[str, Any],
                     selected: dict[str, Any] | None,
                     additional_sources: list[dict[str, Any]] | tuple[()] = ()) -> dict[str, Any]:
        if selected:
            return verify_selection(objects, selected, work_id=work, scene_id=scene_id, basis=basis)
        # Stable operation/basis cache preserves a completed original if a later
        # scene or coverage author fails. No model call under an IO lock.
        path = objects._path('director-narrative-selections', [operation, work, scene_id, basis])
        if path.exists():
            return verify_selection(objects, objects._read(path), work_id=work, scene_id=scene_id, basis=basis)
        method = author.scene_treatment if scene_id else author.film_treatment
        original = await method(request, packet)
        config = getattr(getattr(author, 'client', None), 'config', None)
        host_authored = config is not None and config.authorship_for('direction') == 'HOST'
        selected = retain_selection(objects, work_id=work, scene_id=scene_id, text=original.text,
            basis=basis, selected_by='HOST' if host_authored else 'DIRECTOR_AUTHOR_CANDIDATE',
            reason='Use the selected Host original; production adoption remains pending.' if host_authored else
                   'Use the Director-authored candidate for coverage; Host adoption remains pending.',
            source_refs=[*source_refs, *additional_sources],
            authorship={'actualAuthor': 'HOST' if host_authored else 'MODEL',
                        'model': config.model_for('direction') if config and not host_authored else None})
        with objects._writer():
            if not path.exists():
                objects._write(path, selected)
        return verify_selection(objects, objects._read(path), work_id=work, scene_id=scene_id, basis=basis)

    from drama_plugin.creative_engine.film_identity import narrative_inputs, identity_view
    identity, looks, identity_basis = narrative_inputs(workshop, context, work_id=work,
                                                      scene_id=request.scope.scene_id)
    config = getattr(getattr(author, 'client', None), 'config', None)
    if (config is not None and config.direction_authorship == 'MODEL'
            and not incoming.get('film') and not identity and not looks):
        context = await select_cold_model_film(workshop, author, request, context,
            film_packet(film, source=source, author_context=author_context), operation, source_refs)
        return await native_director_narrative(workshop, author,
            request.model_copy(update={'screenplay_context': context}), operation=operation)
    if looks or 'filmLook' in context:
        context['filmLook'] = workshop.professional_context(context, work_id=work,
            scene_id=request.scope.scene_id)['filmLook']
        source_refs.extend(row['ref'] for row in context['filmLook'])
    if context.get('filmIdentity'):
        source_refs.append(context['filmIdentity']['ref'])
    film_basis = {'screenplayHash': sha256_canonical(film), **identity_basis}
    selected_film = await choose(None, film_basis,
        film_packet(film, source=source, author_context=author_context,
                    film_identity=identity, film_look=looks), incoming.get('film'))
    selected_scenes = {}
    scene_sources = {row['screenplay']['sceneId']: row['screenplayRef']
                     for row in context.get('selectedSceneScreenplays', ())}
    for index, (sid, text) in enumerate(scenes):
        neighbors = [{'relation': 'previous' if i < index else 'next', 'screenplay': scenes[i][1]}
                     for i in (index - 1, index + 1) if 0 <= i < len(scenes)]
        basis = {'screenplayHash': sha256_canonical(text),
                 'filmNarrativeFingerprint': selected_film['ref']['fingerprint']}
        selected_scenes[sid] = await choose(sid, basis,
            scene_packet(text, film_screenplay=film, film_direction=selected_film['text'],
                         neighbors=neighbors, author_context=author_context,
                         film_identity=identity_view(context, sid), film_look=looks),
            incoming.get('scenes', {}).get(sid),
            [selected_film['ref'], *([scene_sources[sid]] if sid in scene_sources else [])])
    context['directorNarrative'] = {'film': selected_film, 'scenes': selected_scenes}
    if context.get('selectedSceneScreenplays'):
        # Existing asset/scene readers resolve these exact per-scene handoffs.
        # Keep the selected prose there as well as in the film author's view.
        context['selectedSceneScreenplays'] = [{**row, 'directorNarrative': selected_view(
            context, row['screenplay']['sceneId'])} for row in context['selectedSceneScreenplays']]
    return context


def bind_host_narrative(workshop: ScreenplayWorkshop, handoff_ref: SourcePin, *, work_id: str,
                        scene_id: str | None, film_text: str, scene_text: str | None,
                        reason: str, scene_texts: dict[str, str] | None = None) -> SourcePin:
    """Select supplied Host prose, not an opinion-history sweep or Canon change."""
    context = workshop.bound_packet(handoff_ref, work_id=work_id, scene_id=scene_id)
    if context is None or context.get('schemaVersion') != 'scene-screenplay-shot-handoff-v1':
        raise ValueError('Director prose requires a selected screenplay handoff')
    body = context['screenplay']
    if scene_texts and (scene_id is not None or scene_text is not None):
        raise ValueError('Choose a current scene text or full-film scene selections, not both')
    scene_bodies = {row['screenplay']['sceneId']: row for row in context.get('selectedSceneScreenplays', ())}
    if set(scene_texts or {}) - set(scene_bodies):
        raise ValueError('Director scene selections need exact selected scene screenplays')
    if scene_id is None:
        if scene_text is not None:
            raise ValueError('Scene prose requires its selected scene screenplay')
        film = body['text']
    else:
        session = workshop.load(context['sessionId'])
        assert session.full_film_ref is not None
        film = workshop.objects.read_ref(session.full_film_ref)['text']
    from drama_plugin.creative_engine.film_identity import narrative_inputs
    _, _, identity_basis = narrative_inputs(workshop, context, work_id=work_id, scene_id=scene_id)
    film_basis = {'screenplayHash': sha256_canonical(film), **identity_basis}
    original = retain_selection(workshop.objects, work_id=work_id, scene_id=None,
        text=film_text, basis=film_basis,
        selected_by='HOST', reason=reason, source_refs=[dump_contract(handoff_ref)])
    # Reuse an exact previously selected film when binding a scene, so its
    # fingerprint remains the same across the whole film and child originals.
    previous = selected_view(context).get('film')
    if (previous and previous['text'] == film_text and previous['selectedBy'] == 'HOST'
            and previous['selectionReason'] == reason and previous.get('basis') == film_basis):
        original = verify_selection(workshop.objects, previous, work_id=work_id, scene_id=None,
                                    basis=film_basis)
    selected: dict[str, Any] = {'film': original, 'scenes': {}}
    if scene_text is not None:
        selected['scenes'][scene_id] = retain_selection(workshop.objects, work_id=work_id,
            scene_id=scene_id, text=scene_text, basis={'screenplayHash': sha256_canonical(body['text']),
                'filmNarrativeFingerprint': original['ref']['fingerprint']},
            selected_by='HOST', reason=reason, source_refs=[dump_contract(handoff_ref), original['ref']])
    for sid, text in (scene_texts or {}).items():
        selected['scenes'][sid] = retain_selection(workshop.objects, work_id=work_id, scene_id=sid,
            text=text, basis={'screenplayHash': sha256_canonical(scene_bodies[sid]['screenplay']['text']),
                'filmNarrativeFingerprint': original['ref']['fingerprint']}, selected_by='HOST', reason=reason,
            source_refs=[scene_bodies[sid]['screenplayRef'], original['ref']])
    return workshop.objects.put('selected-director-handoff:' + (scene_id or work_id),
                                {**context, 'directorNarrative': selected})


async def select_cold_model_film(workshop, author, request, context, packet, operation, source_refs):
    """Reuse pending Host selection/binding; the model owns all three originals.

    Explicit per-role MODEL opts into this cold-start path. Historical global
    MODEL/selected prose retains its old shape; no frozen output is reauthored.
    """
    from drama_plugin.creative_engine.host_text import request_packet, selected_content
    from drama_plugin.creative_engine.screenplay import ContextOriginal
    from drama_plugin.creative_engine.diagnostics import response_context
    from drama_plugin.creative_engine.film_identity import bind_identity
    work = request.scope.work_id; objects = workshop.objects
    path = objects._path('director-film-candidates', [operation, work, packet, author.execution_fingerprint()])
    if path.exists():
        candidate_ref = SourcePin.model_validate(objects._read(path))
        candidate = objects.read_ref(candidate_ref)
    else:
        original = await author.film_treatment(request, packet)
        diagnostic = response_context.get()
        candidate = {'schemaVersion': 'director-film-candidate-v1', 'workId': work,
            'actualAuthor': 'MODEL', 'requestedModel': author.client.config.direction_model,
            'model': diagnostic.model if diagnostic else author.client.config.direction_model,
            'formalAdoption': False, 'sourceRefs': source_refs,
            'original': original.model_dump(),
            'responseEvidence': diagnostic.model_dump() if diagnostic else None}
        candidate_ref = objects.put('director-film-candidate:' + work, candidate)
        with objects._writer():
            objects._write(path, dump_contract(candidate_ref))
    selection_packet = request_packet('film.director-candidate-selection:v1', request,
        {'candidateRef': dump_contract(candidate_ref), 'candidate': candidate},
        {'type': 'object', 'properties': {'candidateFingerprint': {'const': candidate_ref.fingerprint},
            'reason': {'type': 'string', 'minLength': 1}}, 'required': ['candidateFingerprint', 'reason'],
            'additionalProperties': False},
        'Read and select this model-authored candidate as the experimental basis, or leave it unselected. '
        'Host authors only the choice/reason, not replacement world/look/director prose. Not formal adoption.')
    choice = selected_content(request, selection_packet, workshop.host_author_original)
    if (not isinstance(choice, dict) or set(choice) != {'candidateFingerprint', 'reason'}
            or choice['candidateFingerprint'] != candidate_ref.fingerprint
            or not isinstance(choice['reason'], str) or not choice['reason'].strip()):
        raise ValueError('Director candidate selection must reference exact model original')
    refs = {}
    for name in ('world', 'look'):
        refs[name] = workshop.retain_context(ContextOriginal(work_id=work, label='Director ' + name,
            status='AUTHOR_CONCEPT', text=candidate['original'][name],
            authority_ref='director-film-candidate:' + candidate_ref.fingerprint))
    selected = deepcopy(context)
    selected['filmIdentity'] = bind_identity(workshop, work_id=work, scene_id=request.scope.scene_id,
        world_ref=refs['world'], look_ref=refs['look'], analysis_ref=None, scene_state_refs=None,
        reason=choice['reason'])
    basis = {'screenplayHash': sha256_canonical(packet['screenplay']),
             'filmIdentityFingerprint': selected['filmIdentity']['ref']['fingerprint']}
    film = retain_selection(objects, work_id=work, scene_id=None, text=candidate['original']['text'],
        basis=basis, selected_by='HOST', reason=choice['reason'],
        source_refs=[*source_refs, dump_contract(candidate_ref), selected['filmIdentity']['ref']],
        authorship={'actualAuthor': 'MODEL', 'model': candidate['model'],
                    'candidateRef': dump_contract(candidate_ref)})
    selected['directorNarrative'] = {'film': film, 'scenes': {}}
    return selected
