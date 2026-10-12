"""Persist exact Native task/screenplay originals in existing business envelopes.

This is a readback-checked memory projection, never a Canon writer, selection
pointer or production owner. Explicit pins, not an inferred latest version.
"""
from __future__ import annotations
from typing import Any, TYPE_CHECKING
from drama_plugin.contracts.base import canonical_json, dump_contract
from drama_plugin.contracts.creation import Work
from drama_plugin.creative_engine.contracts import Kind, VersionRef
from drama_plugin.exceptions import ConfigurationError

if TYPE_CHECKING:
    from drama_plugin.creative_engine.store import CreativeVersionStore
    from drama_plugin.providers.base import MemoryProvider
    from drama_plugin.film_storage.storage import FilmStorage


class NativeTaskPersistence:
    def __init__(self, versions: CreativeVersionStore, memory: MemoryProvider):
        self.versions, self.memory = versions, memory
        self.film_storage: FilmStorage | None = None

    @property
    def enabled(self) -> bool:
        if self.film_storage is not None:
            return True
        if not hasattr(self.memory,'persist_native_task'):
            return False
        http=getattr(self.memory,'http',None)
        return http is None or 'persist_native_task' in http.config.operations

    def plan(self, refs: tuple[VersionRef, ...]) -> dict[str, Any]:
        versions = [self.versions.resolve(ref) for ref in refs]
        sources = [v for v in versions if v.kind == Kind.SOURCE]
        if len(sources) != 1:
            raise ValueError('EXACT_NATIVE_TASK_SOURCE_REQUIRED')
        source = sources[0]
        if any(v.scope.work_id != source.scope.work_id for v in versions):
            raise ValueError('NATIVE_TASK_PERSISTENCE_CROSS_WORK')
        def original(v: Any) -> dict[str, Any]:
            return {'ref': dump_contract(v.ref()), 'originJson': canonical_json(
                v.model_dump(mode='json', by_alias=True, exclude={'fingerprint'}))}
        # Reviewed author candidates remain candidates. Task creation requires its
        # existing designated Source; screenplay storage consumes adopted versions.
        adopted = [v for v in versions if v.state == 'ADOPTED' and v.scope.shot_id is None]
        return {'source': original(source),
            'works': [original(v) for v in adopted if v.kind == Kind.WORK and v.scope.scene_id is None],
            'scripts': [original(v) for v in adopted if (v.kind == Kind.SCRIPT and v.scope.scene_id is None)
                        or (v.kind == Kind.SCENE and v.scope.scene_id is not None)]}

    async def persist(self, refs: tuple[VersionRef, ...]) -> Work:
        if self.film_storage is not None:
            return await self.film_storage.persist_refs(refs)
        plan = self.plan(refs)
        method = getattr(self.memory, 'persist_native_task', None)
        if method is None:
            raise ConfigurationError('Existing memory provider does not support same-ID Native task persistence')
        work = await method(plan)
        source = next(self.versions.resolve(r) for r in refs if self.versions.resolve(r).kind == Kind.SOURCE)
        expected = source.scope.work_id
        readback = await self.memory.get_work(expected)
        if work.id != expected or readback.id != expected:
            raise ValueError('NATIVE_TASK_PERSISTENCE_ID_CHANGED')
        task = readback.content.get('nativeTask', {})
        if (task.get('authority'), task.get('storageRole')) != ('PLUGIN_NATIVE_ORIGINAL', 'TASK'):
            raise ValueError('NATIVE_TASK_PERSISTENCE_AUTHORITY_MISMATCH')
        for record in (plan['source'], *plan['works']):
            if task.get('originals', {}).get(record['ref']['fingerprint']) != record:
                raise ValueError('NATIVE_TASK_ORIGINAL_READBACK_MISMATCH')
        for record in plan['scripts']:
            script = await self.memory.get_script(record['ref']['identity'])
            retained = script.content.get('nativeScript', {})
            if (script.work_id != expected or script.id != record['ref']['identity']
                    or retained.get('authority') != 'PLUGIN_NATIVE_ORIGINAL'
                    or retained.get('storageRole') != 'SCREENPLAY'
                    or retained.get('originals', {}).get(record['ref']['fingerprint']) != record):
                raise ValueError('NATIVE_SCREENPLAY_ORIGINAL_READBACK_MISMATCH')
        return readback


def register_native_persistence_tools(registry: Any, owner: NativeTaskPersistence) -> None:
    from drama_plugin.tools.catalog import _domain_tool
    async def persist_task(refs: tuple[VersionRef, ...]) -> Work:
        return await owner.persist(refs)
    registry.register(_domain_tool('native_creative.persist_task',
        'Persist this exact Native task ID and selected adopted full-film/scene screenplay originals '
        'in existing Work/Script memory. No new adoption, media, budget or Runtime transition.',
        persist_task, Work, required={'refs': tuple[VersionRef, ...]}))
