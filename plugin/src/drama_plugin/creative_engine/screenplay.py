"""Author originals and Host-selected screenplay sidecars on the existing immutable creative artifact IO.

No agent, model, Runtime loop, Canon write, evaluation gate or media operation.
The entry returns an autonomous author packet with project and professional context.
Revision advice is retained after the complete V1; the Host explicitly selects the final text.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from drama_plugin.contracts.base import ContractModel, dump_contract
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
from drama_plugin.hosts.artifact_io import reject_link
from drama_plugin.tools.registry import ToolRegistry, ToolHandler

HOST_AUTONOMOUS = """Create a complete original screenplay as the actual author.
Use the designated source, adopted facts, full-film framework and creative goal.
First finish the whole work or whole scene. Do not first submit an artistic
selection plan, selected highlights, mandatory deletions or a locked realization.
Explore with your own literary and cinematic knowledge. Use explicitly supplied project adaptation authority, creative preferences,
professional context and feedback as inputs. Distinguish binding user boundaries
from advisory methods and historical candidates; neither examples nor tools choose
the story for you. V1 may fully develop action, interaction, words, thought, narration,
space, performance and sound/image imagination as the work needs. No fixed count,
brevity, restraint, silence or deletion preference. Preserve V1 verbatim before
requesting professional support. Afterwards you may keep it completely, expand,
combine, restructure or remove material. Advice never automatically changes it.
When an independent author is called, its output belongs to that author; the Host
coordinates, reviews and selects rather than claiming that authorship.
Candidate invention is not adopted fact. Formal adoption remains with the existing
authority; this workspace grants no production, media or persistence permission.
"""

Status = Literal['DESIGNATED_SOURCE', 'ADOPTED_FACT', 'AUTHOR_CONCEPT', 'OPEN_POSSIBILITY', 'OBSERVED_RESULT']


class ContextOriginal(ContractModel):
    work_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    status: Status
    text: str = Field(min_length=1)
    authority_ref: str | None = None
    observation_ref: str | None = None

    @model_validator(mode='after')
    def provenance(self) -> 'ContextOriginal':
        if self.status == 'ADOPTED_FACT' and not self.authority_ref:
            raise ValueError('Adopted facts require their existing authority reference')
        if self.status == 'OBSERVED_RESULT' and not self.observation_ref:
            raise ValueError('Observed results require actual observation evidence')
        return self


class NarrativeThread(ContractModel):
    work_id: str = Field(min_length=1)
    key: str = Field(min_length=1)
    status: Literal['ADOPTED_FACT', 'AUTHOR_CONCEPT', 'OPEN_POSSIBILITY', 'OBSERVED_RESULT']
    account: str = Field(min_length=1)
    scene_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    source_refs: tuple[SourcePin, ...] = Field(min_length=1)
    # None means no designated payoff; it is neither a defect nor a to-do gate.
    possible_return_scene: str | None = None


class ScreenplaySession(ContractModel):
    session_id: str = Field(min_length=1)
    work_id: str = Field(min_length=1)
    scope: Literal['FILM', 'SCENE']
    scene_id: str | None = None
    goal: str = Field(min_length=1)
    context_ref: SourcePin
    full_film_ref: SourcePin | None = None
    revision: int = 0
    original_v1_ref: SourcePin | None = None
    support_refs: tuple[SourcePin, ...] = ()
    decision_refs: tuple[SourcePin, ...] = ()
    selected_ref: SourcePin | None = None


class ScreenplayWorkshop:
    """Small creation facet, sharing CreativeVersionStore.objects, not another Host."""

    def __init__(self, objects: DirectorArtifactStore):
        self.objects = objects

    def _read(self, ref: SourcePin, schema: str) -> dict[str, Any]:
        value = self.objects.read_ref(ref)
        if value.get('schemaVersion') != schema:
            raise ValueError('Wrong screenplay artifact type')
        return value

    def retain_context(self, original: ContextOriginal) -> SourcePin:
        original = ContextOriginal.model_validate(dump_contract(original))
        return self.objects.put('screenplay-context:' + original.label,
            {'schemaVersion': 'screenplay-context-v1', **dump_contract(original)})

    def retain_thread(self, thread: NarrativeThread) -> SourcePin:
        thread = NarrativeThread.model_validate(dump_contract(thread))
        sources = [self._read(ref, 'screenplay-context-v1') for ref in thread.source_refs]
        if any(s['workId'] != thread.work_id for s in sources):
            raise ValueError('Long-arc source work mismatch')
        if thread.status in {'ADOPTED_FACT', 'OBSERVED_RESULT'} and any(s['status'] != thread.status for s in sources):
            raise ValueError('A candidate or possibility cannot become adopted/observed memory')
        ref = self.objects.put('narrative-thread:' + thread.key,
            {'schemaVersion': 'narrative-thread-v1', **dump_contract(thread)})
        path = self.objects._path('narrative-index', thread.work_id)
        with self.objects.io.guard(self.objects.root / '.screenplay-index.lock'):
            reject_link(path)
            refs = self.objects._read(path)['refs'] if path.exists() else []
            if dump_contract(ref) not in refs:
                self.objects._write(path, {'refs': [*refs, dump_contract(ref)]})
        return ref

    def relevant_memory(self, work_id: str, scene_id: str | None, *, tags: tuple[str, ...] = (),
                        include_refs: tuple[SourcePin, ...] = (), only_refs: bool = False) -> list[dict[str, Any]]:
        path = self.objects._path('narrative-index', work_id)
        reject_link(path)
        refs = [SourcePin.model_validate(r) for r in self.objects._read(path)['refs']] if path.exists() else []
        selected = {r.fingerprint for r in include_refs}
        latest: dict[tuple[str, str], SourcePin] = {}
        for ref in refs:
            indexed = self._read(ref, 'narrative-thread-v1')
            latest[(indexed['key'], indexed['status'])] = ref
        # A pinned handoff remains portable when its originals are available
        # without the mutable discovery index. Read explicit refs only; absence
        # from the index does not authorize calling an old thread current.
        refs += [ref for ref in include_refs if ref not in refs]
        rows = []
        for ref in refs:
            row = self._read(ref, 'narrative-thread-v1')
            if row['workId'] != work_id:
                raise ValueError('Long-arc index work mismatch')
            if only_refs and ref.fingerprint not in selected:
                continue
            if latest.get((row['key'], row['status'])) != ref and ref.fingerprint not in selected:
                continue
            # Current scope membership and author-selected topics, never adjacency.
            relevant = scene_id in row['sceneIds'] or bool(set(tags) & set(row['tags'])) or ref.fingerprint in selected
            if not relevant:
                continue
            # An earlier candidate is opt-in, not an automatic answer for a new V1.
            if row['status'] in {'AUTHOR_CONCEPT', 'OPEN_POSSIBILITY'} and ref.fingerprint not in selected:
                continue
            rows.append({'ref': dump_contract(ref), 'current': latest.get((row['key'], row['status'])) == ref, **row})
        if selected - {r['ref']['fingerprint'] for r in rows}:
            raise ValueError('Selected long-arc thread is absent or belongs to another work')
        return rows

    def _path(self, session_id: str) -> Path:
        return self.objects._path('screenplay-sessions', session_id)

    def load(self, session_id: str) -> ScreenplaySession:
        session = ScreenplaySession.model_validate(self.objects._read(self._path(session_id)))
        if session.session_id != session_id:
            raise ValueError('Screenplay session identity mismatch')
        return session

    def _save(self, session: ScreenplaySession, expected_revision: int) -> None:
        path = self._path(session.session_id)
        current = self.load(session.session_id)
        if current.revision != expected_revision:
            raise ValueError('Screenplay session revision conflict')
        session.revision = expected_revision + 1
        self.objects._write(path, dump_contract(session))

    def begin(self, *, session_id: str, work_id: str, scope: Literal['FILM', 'SCENE'], goal: str,
              source_refs: tuple[SourcePin, ...], scene_id: str | None = None,
              full_film_ref: SourcePin | None = None, memory_tags: tuple[str, ...] = (),
              memory_refs: tuple[SourcePin, ...] = (), memory_refs_only: bool = False,
              author_context: dict[str, Any] | None = None) -> dict[str, Any]:
        sources = [self._read(ref, 'screenplay-context-v1') for ref in source_refs]
        if not sources or any(s['workId'] != work_id for s in sources):
            raise ValueError('Screenplay source work mismatch or missing source')
        if any(s['status'] in {'AUTHOR_CONCEPT', 'OPEN_POSSIBILITY'} and ref != full_film_ref
               for ref, s in zip(source_refs, sources, strict=True)):
            raise ValueError('Initial source facts cannot silently include candidate solutions')
        if scope == 'SCENE':
            if not scene_id or full_film_ref is None or full_film_ref not in source_refs:
                raise ValueError('A scene needs the complete film framework in its context')
        memory = self.relevant_memory(work_id, scene_id, tags=memory_tags, include_refs=memory_refs, only_refs=memory_refs_only)
        packet = {'schemaVersion': 'autonomous-screenplay-context-v1', 'workId': work_id,
            'scope': scope, 'sceneId': scene_id, 'goal': goal, 'instruction': HOST_AUTONOMOUS,
            'sources': [{'ref': dump_contract(ref), **s} for ref, s in zip(source_refs, sources, strict=True)],
            'longArcMemory': memory, 'professionalGuidance': [], 'historicalCandidates': [],
            'authorContext': author_context or {}}
        context_ref = self.objects.put('screenplay-packet:' + session_id, packet)
        session = ScreenplaySession(session_id=session_id, work_id=work_id, scope=scope,
            scene_id=scene_id, goal=goal, context_ref=context_ref, full_film_ref=full_film_ref)
        with self.objects.io.guard(self.objects.root / '.screenplay-index.lock'):
            if self._path(session_id).exists():
                raise ValueError('Existing screenplay session; load the preserved originals')
            self.objects._write(self._path(session_id), dump_contract(session))
        return {'session': dump_contract(session), 'authorPacket': packet}

    def retain_v1(self, session_id: str, text: str, *, expected_revision: int = 0) -> SourcePin:
        if not text.strip():
            raise ValueError('A complete screenplay body is required')
        with self.objects.io.guard(self.objects.root / '.screenplay-index.lock'):
            session = self.load(session_id)
            if session.original_v1_ref:
                original = self._read(session.original_v1_ref, 'director-screenplay-v1')
                if original['text'] == text:
                    return session.original_v1_ref
                raise ValueError('Original V1 is immutable; create a subsequent decision version')
            ref = self.objects.put('screenplay:' + session_id + ':V1', {
                'schemaVersion': 'director-screenplay-v1', 'workId': session.work_id,
                'scope': session.scope, 'sceneId': session.scene_id, 'version': 1,
                'status': 'AUTHOR_CANDIDATE', 'contextRef': dump_contract(session.context_ref), 'text': text})
            session.original_v1_ref = ref
            self._save(session, expected_revision)
            return ref

    def support_packet(self, session_id: str, *, specialty: str, question: str) -> dict[str, Any]:
        session = self.load(session_id)
        if not session.original_v1_ref:
            raise ValueError('Complete and preserve V1 before professional support')
        return {'role': 'ADVISORY_SUPPORT', 'specialty': specialty, 'question': question,
            'originalRef': dump_contract(session.original_v1_ref),
            'original': self._read(session.original_v1_ref, 'director-screenplay-v1'),
            'context': self._read(session.context_ref, 'autonomous-screenplay-context-v1'),
            'instruction': 'Offer creative support, competing possibilities, gains and costs. The Host may keep everything. Do not replace its work or require a revision, deletion, consensus or score.'}

    def retain_support(self, session_id: str, *, specialty: str, text: str, expected_revision: int) -> SourcePin:
        if not text.strip():
            raise ValueError('Empty support')
        with self.objects.io.guard(self.objects.root / '.screenplay-index.lock'):
            session = self.load(session_id)
            if not session.original_v1_ref:
                raise ValueError('Complete and preserve V1 before professional support')
            ref = self.objects.put('screenplay-support:' + session_id + ':' + specialty, {
                'schemaVersion': 'screenplay-support-v1', 'workId': session.work_id,
                'sessionId': session_id, 'originalRef': dump_contract(session.original_v1_ref),
                'specialty': specialty, 'authority': 'ADVISORY', 'text': text})
            session.support_refs = (*session.support_refs, ref)
            self._save(session, expected_revision)
            return ref

    def decide(self, session_id: str, *, choice: Literal['KEEP_ALL', 'DEVELOP', 'RESTRUCTURE', 'REDUCE'],
               reason: str, expected_revision: int, text: str | None = None) -> SourcePin:
        if choice not in {'KEEP_ALL', 'DEVELOP', 'RESTRUCTURE', 'REDUCE'}:
            raise ValueError('Unsupported Host artistic decision')
        if not reason.strip():
            raise ValueError('Record the Host decision and its artistic reason')
        with self.objects.io.guard(self.objects.root / '.screenplay-index.lock'):
            session = self.load(session_id)
            if not session.original_v1_ref:
                raise ValueError('Complete and preserve V1 before deciding')
            if choice == 'KEEP_ALL':
                if text is not None:
                    raise ValueError('KEEP_ALL selects the exact original, without replacement text')
                selected = session.original_v1_ref
            else:
                if text is None or not text.strip():
                    raise ValueError('A revision needs its full continuous screenplay')
                selected = self.objects.put('screenplay:' + session_id + ':revision', {
                    'schemaVersion': 'director-screenplay-v1', 'workId': session.work_id,
                    'scope': session.scope, 'sceneId': session.scene_id,
                    'version': len(session.decision_refs) + 2, 'status': 'AUTHOR_CANDIDATE',
                    'originalRef': dump_contract(session.original_v1_ref),
                    'contextRef': dump_contract(session.context_ref), 'text': text})
            decision = self.objects.put('screenplay-decision:' + session_id, {
                'schemaVersion': 'host-artistic-decision-v1', 'sessionId': session_id,
                'authority': 'HOST', 'choice': choice, 'reason': reason,
                'originalRef': dump_contract(session.original_v1_ref), 'selectedRef': dump_contract(selected),
                'supportRefs': [dump_contract(r) for r in session.support_refs], 'formalAdoption': False})
            session.selected_ref = selected
            session.decision_refs = (*session.decision_refs, decision)
            self._save(session, expected_revision)
            return selected

    def selected_packet(self, session_id: str) -> dict[str, Any]:
        session = self.load(session_id)
        if not session.selected_ref:
            raise ValueError('The Host must select a screenplay before shot realization')
        return {'schemaVersion': 'scene-screenplay-shot-handoff-v1', 'sessionId': session_id,
            'screenplayRef': dump_contract(session.selected_ref),
            'screenplay': self._read(session.selected_ref, 'director-screenplay-v1'),
            'context': self._read(session.context_ref, 'autonomous-screenplay-context-v1'),
            'decisionRef': dump_contract(session.decision_refs[-1]),
            'authority': 'AUTHOR_CANDIDATE', 'use': 'TEXT_DESIGN_ONLY', 'formalAdoptionRequired': True,
            'instruction': 'Develop the complete selected scene through meaningful performance and sound/image choices. No detail quota. Preserve its intent and words; proposals that change them return to the Host. Formal production must use the existing exact adopted source/version mechanism.'}

    def shot_handoff(self, session_id: str) -> dict[str, Any]:
        if self.load(session_id).scope != 'SCENE':
            raise ValueError('Complete a scene screenplay before shot design')
        return self.selected_packet(session_id)

    def bind_selection(self, session_id: str, *, work_id: str, scene_id: str | None) -> SourcePin:
        session = self.load(session_id)
        if (session.work_id, session.scene_id) != (work_id, scene_id):
            raise ValueError('Screenplay handoff scope mismatch')
        if session.scope != ('SCENE' if scene_id else 'FILM'):
            raise ValueError('Screenplay handoff level mismatch')
        return self.objects.put('screenplay-handoff:' + session_id, self.selected_packet(session_id))

    def bound_packet(self, ref: SourcePin | None, *, work_id: str, scene_id: str | None) -> dict[str, Any] | None:
        if ref is None:
            return None
        packet = self.objects.read_ref(ref)
        if packet.get('schemaVersion') == 'native-screenplay-context-v1':
            if (packet['workId'], packet['sceneId']) != (work_id, scene_id):
                raise ValueError('Bound screenplay context scope mismatch')
            return packet
        if packet.get('schemaVersion') != 'scene-screenplay-shot-handoff-v1':
            raise ValueError('Wrong screenplay handoff type')
        screenplay = packet['screenplay']
        if (screenplay['workId'], screenplay['sceneId']) != (work_id, scene_id):
            raise ValueError('Bound screenplay scope mismatch')
        self.objects.read_ref(SourcePin.model_validate(packet['screenplayRef']))
        return packet

    def host_author_original(self, packet: dict[str, Any]) -> dict[str, Any] | None:
        """Resolve one exact selected original; retain a readable missing-text request."""
        work = packet['scope']['workId']
        identity = [work, packet['task'], packet['inputFingerprint']]
        path = self.objects._path('host-author-selections', identity)
        if path.exists():
            ref = SourcePin.model_validate(self.objects._read(path))
            return {'ref': dump_contract(ref), 'original': self.objects.read_ref(ref)}
        ref = self.objects.put('host-author-request:' + work, packet)
        with self.objects._writer():
            self.objects._write(self.objects._path('host-author-requests', work), dump_contract(ref))
            self.objects._write(self.objects._path('host-author-request-inputs', identity), dump_contract(ref))
        return None

    def host_author_request(self, work_id: str) -> dict[str, Any]:
        path = self.objects._path('host-author-requests', work_id)
        if not path.exists():
            raise ValueError('No missing Host text request for this Work')
        return self.objects.read_ref(SourcePin.model_validate(self.objects._read(path)))

    def bind_host_author_original(self, handoff_ref: SourcePin | None, *, work_id: str,
                                  scene_id: str | None, task: str, input_fingerprint: str,
                                  content: Any, reason: str) -> SourcePin:
        """Select Host text/DTO in the existing original store; no author or adoption."""
        from copy import deepcopy
        import re
        if not task.strip() or not reason.strip() or not re.fullmatch(r'[a-f0-9]{64}', input_fingerprint):
            raise ValueError('Host original needs exact task/input fingerprint and selection reason')
        request_path = self.objects._path('host-author-request-inputs', [work_id, task, input_fingerprint])
        if not request_path.exists():
            raise ValueError('Host original requires an exact pending author request')
        request_ref = SourcePin.model_validate(self.objects._read(request_path))
        pending = self.objects.read_ref(request_ref)
        if pending['scope']['sceneId'] != scene_id:
            raise ValueError('Host original request scope mismatch')
        packet = deepcopy(self.bound_packet(handoff_ref, work_id=work_id, scene_id=scene_id)) if handoff_ref else None
        original = {'schemaVersion': 'host-author-original-v1', 'version': 1,
            'workId': work_id, 'sceneId': scene_id, 'task': task, 'inputFingerprint': input_fingerprint,
            'content': content, 'actualAuthor': 'HOST', 'selectedBy': 'HOST',
            'selectionReason': reason, 'formalAdoption': False, 'sourceRef': dump_contract(request_ref)}
        ref = self.objects.put('host-author-original:' + task, original)
        with self.objects._writer():
            self.objects._write(self.objects._path('host-author-selections', [work_id, task, input_fingerprint]), dump_contract(ref))
        if packet is None:
            return ref
        container = packet if 'authorContext' in packet or 'context' not in packet else packet['context']
        context = container.setdefault('authorContext', {})
        context.setdefault('hostAuthoring', {})[task + ':' + input_fingerprint] = {
            'ref': dump_contract(ref), 'original': original}
        return self.objects.put('host-author-handoff:' + (scene_id or work_id), packet)

    def bind_director_narrative(self, handoff_ref: SourcePin, *, work_id: str,
                               scene_id: str | None, film_text: str, reason: str,
                               scene_text: str | None = None, scene_texts: dict[str, str] | None = None) -> SourcePin:
        from drama_plugin.creative_engine.direction_narrative import bind_host_narrative
        return bind_host_narrative(self, handoff_ref, work_id=work_id, scene_id=scene_id,
            film_text=film_text, scene_text=scene_text, reason=reason, scene_texts=scene_texts)

    def bind_professional_context(self, handoff_ref: SourcePin, *, work_id: str,
                                  scene_id: str | None, design_refs: tuple[SourcePin, ...]) -> SourcePin:
        """Bind selected designs after the Host film or scene decision.

        Preserve screenplay and evidence. No history scan, Canon adoption,
        competing design store or prewriting rules.
        """
        packet = self.bound_packet(handoff_ref, work_id=work_id, scene_id=scene_id)
        if packet is None or packet.get('schemaVersion') != 'scene-screenplay-shot-handoff-v1':
            raise ValueError('Professional designs require a selected complete screenplay')
        updated = {**packet, 'professionalDesignRefs': [dump_contract(r) for r in design_refs]}
        self.professional_context(updated, work_id=work_id, scene_id=scene_id)
        return self.objects.put('scene-professional-handoff:' + (scene_id or work_id), updated)

    def professional_context(self, packet: dict[str, Any] | None, *, work_id: str,
                             scene_id: str | None) -> dict[str, Any]:
        from drama_plugin.contracts.film_grammar import WorkDirectingAuthority
        from drama_plugin.contracts.location_design import LocationDesign
        result: dict[str, Any] = {'workId': work_id, 'sceneId': scene_id,
                                 'filmLook': [], 'locationCandidates': []}
        for raw in (packet or {}).get('professionalDesignRefs', []):
            ref = SourcePin.model_validate(raw)
            body = self.objects.read_ref(ref)
            if body.get('schemaVersion') == 'work-directing-authority-v1':
                look = WorkDirectingAuthority.model_validate(body)
                if look.work_scope != work_id:
                    raise ValueError('Professional Film Look work mismatch')
                result['filmLook'].append({'ref': dump_contract(ref), 'design': dump_contract(look)})
            elif body.get('schemaVersion') == 'location-design-v2':
                place = LocationDesign.model_validate(body)
                if scene_id not in place.scene_refs:
                    raise ValueError('Professional location scope mismatch')
                result['locationCandidates'].append({'selection': len(result['locationCandidates']),
                    'ref': dump_contract(ref), 'design': dump_contract(place)})
            else:
                raise ValueError('Unsupported professional continuity original')
        return result

    def bind_context(self, *, work_id: str, scene_id: str | None) -> SourcePin:
        return self.objects.put('native-screenplay-context:' + work_id, {
            'schemaVersion': 'native-screenplay-context-v1', 'workId': work_id, 'sceneId': scene_id,
            'longArcMemory': self.relevant_memory(work_id, scene_id, tags=('full-film',) if scene_id is None else ())})

    def native_original(self, operation: str, *, work_id: str, scope: str, scene_id: str | None, text: str,
                        source_refs: list[dict[str, Any]]) -> SourcePin:
        """Default native Canon paths preserve full originals before direction/support."""
        ref = self.objects.put('native-screenplay-v1:' + operation + ':' + (scene_id or 'film'), {
            'schemaVersion': 'native-director-screenplay-v1', 'workId': work_id,
            'scope': scope, 'sceneId': scene_id, 'status': 'AUTHOR_CANDIDATE',
            'text': text, 'sourceRefs': source_refs, 'operation': operation})
        path = self.objects._path('native-screenplay-index', [work_id, scope, scene_id])
        with self.objects.io.guard(self.objects.root / '.screenplay-index.lock'):
            refs = self.objects._read(path)['refs'] if path.exists() else []
            if dump_contract(ref) not in refs:
                self.objects._write(path, {'refs': [*refs, dump_contract(ref)]})
        return ref


def register_screenplay_tools(registry: 'ToolRegistry', workshop: ScreenplayWorkshop, *, continue_host: Any = None) -> None:
    """The real Plugin registry exposes the same local facet to any Host transport."""
    from drama_plugin.tools.catalog import _domain_tool
    async def retain_context(original: ContextOriginal) -> SourcePin:
        return workshop.retain_context(ContextOriginal.model_validate(original))
    async def host_author_request(work_id: str) -> dict[str, Any]:
        return workshop.host_author_request(work_id)
    async def bind_host_author_original(handoff_ref: SourcePin | None, work_id: str, scene_id: str | None,
                                        task: str, input_fingerprint: str, content: Any, reason: str, run_id: str | None = None) -> SourcePin:
        if run_id is not None and continue_host is None:
            raise ValueError('Host continuation is unavailable')
        if run_id is not None:
            await continue_host(run_id, work_id, input_fingerprint, None)
        ref = workshop.bind_host_author_original(SourcePin.model_validate(handoff_ref) if handoff_ref else None, work_id=work_id,
            scene_id=scene_id, task=task, input_fingerprint=input_fingerprint, content=content, reason=reason)
        if run_id is not None:
            selected = workshop.host_author_original({'scope': {'workId': work_id},
                'task': task, 'inputFingerprint': input_fingerprint})
            assert selected is not None
            await continue_host(run_id, work_id, input_fingerprint, SourcePin.model_validate(selected['ref']))
        return ref
    async def bind_director_narrative(handoff_ref: SourcePin, work_id: str, scene_id: str | None,
                                      film_text: str, reason: str, scene_text: str | None = None,
                                      scene_texts: dict[str, str] | None = None) -> SourcePin:
        return workshop.bind_director_narrative(SourcePin.model_validate(handoff_ref),
            work_id=work_id, scene_id=scene_id, film_text=film_text, scene_text=scene_text, reason=reason, scene_texts=scene_texts)
    async def bind_professional_context(handoff_ref: SourcePin, work_id: str, scene_id: str | None,
                                       design_refs: tuple[SourcePin, ...]) -> SourcePin:
        return workshop.bind_professional_context(SourcePin.model_validate(handoff_ref), work_id=work_id,
            scene_id=scene_id, design_refs=tuple(SourcePin.model_validate(r) for r in design_refs))
    async def retain_thread(thread: NarrativeThread) -> SourcePin:
        return workshop.retain_thread(NarrativeThread.model_validate(thread))
    async def begin(session_id: str, work_id: str, scope: Literal['FILM', 'SCENE'], goal: str,
                    source_refs: tuple[SourcePin, ...], scene_id: str | None = None,
                    full_film_ref: SourcePin | None = None, memory_tags: tuple[str, ...] = (),
                    memory_refs: tuple[SourcePin, ...] = (), memory_refs_only: bool = False,
              author_context: dict[str, Any] | None = None) -> dict[str, Any]:
        return workshop.begin(session_id=session_id, work_id=work_id, scope=scope, goal=goal,
            source_refs=tuple(SourcePin.model_validate(r) for r in source_refs), scene_id=scene_id,
            full_film_ref=SourcePin.model_validate(full_film_ref) if full_film_ref is not None else None,
            memory_tags=memory_tags, memory_refs=tuple(SourcePin.model_validate(r) for r in memory_refs),
            memory_refs_only=memory_refs_only, author_context=author_context)
    async def retain_v1(session_id: str, text: str, expected_revision: int = 0) -> SourcePin:
        return workshop.retain_v1(session_id, text, expected_revision=expected_revision)
    async def support_packet(session_id: str, specialty: str, question: str) -> dict[str, Any]:
        return workshop.support_packet(session_id, specialty=specialty, question=question)
    async def retain_support(session_id: str, specialty: str, text: str, expected_revision: int) -> SourcePin:
        return workshop.retain_support(session_id, specialty=specialty, text=text, expected_revision=expected_revision)
    async def decide(session_id: str, choice: Literal['KEEP_ALL', 'DEVELOP', 'RESTRUCTURE', 'REDUCE'],
                     reason: str, expected_revision: int, text: str | None = None) -> SourcePin:
        return workshop.decide(session_id, choice=choice, reason=reason, expected_revision=expected_revision, text=text)
    async def shot_handoff(session_id: str) -> dict[str, Any]: return workshop.shot_handoff(session_id)
    specs: list[tuple[str, ToolHandler, Any, dict[str, Any], dict[str, Any]]] = [
        ('host_author_request', host_author_request, dict, {'work_id': str}, {}),
        ('bind_host_author_original', bind_host_author_original, SourcePin,
            {'handoff_ref': SourcePin | None, 'work_id': str, 'scene_id': str | None, 'task': str,
             'input_fingerprint': str, 'content': Any, 'reason': str}, {'run_id': str | None}),
        ('bind_director_narrative', bind_director_narrative, SourcePin,
            {'handoff_ref': SourcePin, 'work_id': str, 'scene_id': str | None, 'film_text': str, 'reason': str},
            {'scene_text': str | None, 'scene_texts': dict[str, str] | None}),
        ('bind_professional_context', bind_professional_context, SourcePin,
            {'handoff_ref': SourcePin, 'work_id': str, 'scene_id': str | None, 'design_refs': tuple[SourcePin, ...]}, {}),
        ('retain_context', retain_context, SourcePin, {'original': ContextOriginal}, {}),
        ('retain_thread', retain_thread, SourcePin, {'thread': NarrativeThread}, {}),
        ('begin', begin, dict, {'session_id': str, 'work_id': str, 'scope': Literal['FILM', 'SCENE'], 'goal': str, 'source_refs': tuple[SourcePin, ...]},
            {'scene_id': str | None, 'full_film_ref': SourcePin | None, 'memory_tags': tuple[str, ...], 'memory_refs': tuple[SourcePin, ...], 'memory_refs_only': bool, 'author_context': dict[str, Any] | None}),
        ('retain_v1', retain_v1, SourcePin, {'session_id': str, 'text': str}, {'expected_revision': int}),
        ('support_packet', support_packet, dict, {'session_id': str, 'specialty': str, 'question': str}, {}),
        ('retain_support', retain_support, SourcePin, {'session_id': str, 'specialty': str, 'text': str, 'expected_revision': int}, {}),
        ('decide', decide, SourcePin, {'session_id': str, 'choice': Literal['KEEP_ALL', 'DEVELOP', 'RESTRUCTURE', 'REDUCE'], 'reason': str, 'expected_revision': int}, {'text': str | None}),
        ('shot_handoff', shot_handoff, dict, {'session_id': str}, {}),
    ]
    for name, handler, output, required, optional in specs:
        registry.register(_domain_tool('screenplay.' + name,
            'Local Host-first creative originals and advice; never Canon adoption or production.',
            handler, output, required=required, optional=optional))
