"""Bounded source-bound author calls inside existing capabilities, no parallel engine.

Interactive Host sessions can request advice and bind their chosen full scene.
The native batch default writes and preserves the whole film before Canon
projection and the whole scene before Direction, each followed by a Host decision.
It supplies those exact candidates to formal projection and realization.
"""
from pydantic import JsonValue, TypeAdapter
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.creative_engine.backends import FormalCanonAuthor
from drama_plugin.creative_engine.contracts import AuthorRequest
from drama_plugin.film.contracts import FilmAuthorRequest
from drama_plugin.creative_engine.screenplay import ContextOriginal, ScreenplayWorkshop


async def native_film_decision(workshop: ScreenplayWorkshop, author: FormalCanonAuthor,
                               request: AuthorRequest | FilmAuthorRequest, *, operation: str,
                               screenplay: str) -> dict[str, JsonValue]:
    """The complete film original already exists; preserve, then ask its Host."""
    incoming = request.screenplay_context or {}
    if incoming.get('schemaVersion') == 'scene-screenplay-shot-handoff-v1':
        return incoming
    identity = 'native-film:' + sha256_canonical([operation, screenplay, incoming])
    if not workshop._path(identity).exists():
        source = workshop.retain_context(ContextOriginal(work_id=request.scope.work_id,
            label=identity + ':source', status='DESIGNATED_SOURCE',
            text=request.source.text or request.source.external_reference or request.source.goal))
        rows = incoming.get('longArcMemory')
        refs = tuple(SourcePin.model_validate(r['ref']) for r in rows if isinstance(r, dict)) if isinstance(rows, list) else ()
        workshop.begin(session_id=identity, work_id=request.scope.work_id, scope='FILM',
            goal=request.source.goal, source_refs=(source,), memory_refs=refs, memory_refs_only=True)
    session = workshop.load(identity)
    if session.original_v1_ref is None:
        workshop.retain_v1(identity, screenplay, expected_revision=session.revision)
        session = workshop.load(identity)
    if session.selected_ref is None:
        assert session.original_v1_ref is not None
        packet = {**workshop.objects.read_ref(session.context_ref),
            'preservedV1': workshop.objects.read_ref(session.original_v1_ref)}
        decision = await author.scene_decision(request, TypeAdapter(dict[str, JsonValue]).validate_python(packet))
        workshop.decide(identity, choice=decision.choice, reason=decision.reason, text=decision.text,
            expected_revision=session.revision)
    return TypeAdapter(dict[str, JsonValue]).validate_python(workshop.selected_packet(identity))


async def native_film_original(workshop: ScreenplayWorkshop, author: FormalCanonAuthor,
                               request: AuthorRequest | FilmAuthorRequest, *, operation: str) -> dict[str, JsonValue]:
    """Whole free original precedes the structured Canon projection in new runs."""
    incoming = request.screenplay_context or {}
    if incoming.get('schemaVersion') == 'scene-screenplay-shot-handoff-v1':
        return incoming
    identity = 'native-first-film:' + sha256_canonical([operation, request.source.model_dump(mode='json'), incoming])
    if not workshop._path(identity).exists():
        source = workshop.retain_context(ContextOriginal(work_id=request.scope.work_id,
            label=identity + ':source', status='DESIGNATED_SOURCE',
            text=request.source.text or request.source.external_reference or request.source.goal))
        rows = incoming.get('longArcMemory')
        refs = tuple(SourcePin.model_validate(r['ref']) for r in rows if isinstance(r, dict)) if isinstance(rows, list) else ()
        workshop.begin(session_id=identity, work_id=request.scope.work_id, scope='FILM',
            goal=request.source.goal, source_refs=(source,), memory_refs=refs, memory_refs_only=True)
    session = workshop.load(identity)
    packet = workshop.objects.read_ref(session.context_ref)
    if session.original_v1_ref is None:
        original = await author.film_original(request, TypeAdapter(dict[str, JsonValue]).validate_python(packet))
        workshop.retain_v1(identity, original.text, expected_revision=session.revision)
        session = workshop.load(identity)
    if session.selected_ref is None:
        assert session.original_v1_ref is not None
        decision = await author.scene_decision(request, TypeAdapter(dict[str, JsonValue]).validate_python({
            **packet, 'preservedV1': workshop.objects.read_ref(session.original_v1_ref)}))
        workshop.decide(identity, choice=decision.choice, reason=decision.reason,
            text=decision.text, expected_revision=session.revision)
    return TypeAdapter(dict[str, JsonValue]).validate_python(workshop.selected_packet(identity))


async def native_scene_screenplay(workshop: ScreenplayWorkshop, author: FormalCanonAuthor,
                                 request: AuthorRequest | FilmAuthorRequest, *, operation: str,
                                 scene_id: str) -> dict[str, JsonValue]:
    json = TypeAdapter(dict[str, JsonValue])
    incoming = request.screenplay_context or {}
    # A later Film output inventory must not change the preserved author session.
    incoming = {k: v for k, v in incoming.items() if k != 'selectedSceneScreenplays'}
    if incoming.get('schemaVersion') == 'scene-screenplay-shot-handoff-v1':
        body = incoming.get('screenplay')
        if isinstance(body, dict) and body.get('scope') == 'SCENE':
            if body.get('sceneId') != scene_id:
                raise ValueError('Selected scene does not match the realization scope')
            return incoming
    assert request.canon is not None
    work_id = request.scope.work_id
    # A retained film candidate may serve as framework, never as adopted fact.
    framework = request.canon.script.screenplay
    if incoming.get('schemaVersion') == 'scene-screenplay-shot-handoff-v1':
        selected = incoming.get('screenplay')
        selected_text = selected.get('text') if isinstance(selected, dict) else None
        if isinstance(selected_text, str):
            framework = selected_text
    identity = 'native-scene:' + sha256_canonical([operation, scene_id, framework, incoming])
    path = workshop._path(identity)
    if not path.exists():
        source = workshop.retain_context(ContextOriginal(work_id=work_id, label=identity + ':source',
            status='DESIGNATED_SOURCE', text=request.source.text or request.source.external_reference or request.source.goal))
        film = workshop.retain_context(ContextOriginal(work_id=work_id, label=identity + ':film',
            status='AUTHOR_CONCEPT', text=framework))
        memory = incoming.get('longArcMemory')
        incoming_context = incoming.get('context')
        if memory is None and isinstance(incoming_context, dict):
            memory = incoming_context.get('longArcMemory')
        memory_refs = tuple(SourcePin.model_validate(row['ref']) for row in memory
            if isinstance(row, dict)) if isinstance(memory, list) else ()
        workshop.begin(session_id=identity, work_id=work_id, scope='SCENE', scene_id=scene_id,
            goal=request.source.goal, source_refs=(source, film), full_film_ref=film,
            memory_refs=memory_refs, memory_refs_only=True)
    session = workshop.load(identity)
    context = workshop.objects.read_ref(session.context_ref)
    if session.original_v1_ref is None:
        original = await author.scene_original(request, json.validate_python(context))
        workshop.retain_v1(identity, original.text, expected_revision=session.revision)
        session = workshop.load(identity)
    if session.selected_ref is None:
        assert session.original_v1_ref is not None
        decision_packet = {**context, 'preservedV1': workshop.objects.read_ref(session.original_v1_ref)}
        decision = await author.scene_decision(request, json.validate_python(decision_packet))
        workshop.decide(identity, choice=decision.choice, reason=decision.reason,
            text=decision.text, expected_revision=session.revision)
    return json.validate_python(workshop.shot_handoff(identity))
