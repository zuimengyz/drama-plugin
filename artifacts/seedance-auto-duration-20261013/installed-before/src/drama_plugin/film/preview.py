"""Offline native request rehearsal: read-only Ledger, volatile bindings/compiler.

No generation child, frozen production Preparation, approval, budget, or HTTP.
"""
from __future__ import annotations

from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.contracts.media import Media
from drama_plugin.creative_engine.contracts import Kind
from drama_plugin.creative_engine.sources import NativeCreativeSources
from drama_plugin.film.media_units import production_progress, completion
from drama_plugin.film.media_references import select_references
from drama_plugin.generation.contracts import GenerationTask, OwnerBindings, MediaBoundary
from drama_plugin.generation.compiler import PromptCompiler
from drama_plugin.generation.operation import OperationResolver, resolve_profile
from drama_plugin.generation.sources import PackageReader
from drama_plugin.production.references import ReferenceExecutionStore
from drama_plugin.runtime.contracts import ArtifactReference


class PreviewLedger:
    def __init__(self, ledger, bindings): self.ledger, self.bindings = ledger, bindings
    def get_artifact(self, kind, ref):
        if kind == 'reference-execution-binding':
            matches = [b for b in self.bindings._current.values() if b.source().artifact_ref == ref.artifact_ref and b.version == ref.version]
            if matches:
                b = matches[0]; return b.model_dump(mode='json',by_alias=True),b.scope,b.source().reference().fingerprint
        return self.ledger.get_artifact(kind,ref)
    def __getattr__(self, name):
        if name.startswith(('put','create','save','reserve','claim','record','update')):
            raise ValueError('PREVIEW_LEDGER_IS_READ_ONLY')
        return getattr(self.ledger,name)


class RetainedMediaReader:
    def __init__(self, p, records):
        self.media = {}
        for row in records:
            done = completion(p,row['runId'])
            if not done: continue
            _, _, binding, _ = done
            if not binding.canonical_media_ref: continue
            self.media[binding.canonical_media_ref.artifact_ref] = Media(id=binding.canonical_media_ref.artifact_ref,
                work_id=binding.scope.work_id,shot_id=binding.scope.shot_id,media_type='VIDEO',mime_type='video/mp4',
                source_ref=binding.provider_result_id,file_size=binding.media.byte_count,content_hash=binding.media.content_hash,
                duration_ms=row['actualDurationMs'])
    async def get_media(self, identity): return self.media[identity]


async def next_unit_preview(p, run_id, *, duration_ms=None, spoken_range=None):
    progress = production_progress(p,run_id); target = progress['nextUnit']
    if target is None: return {'simulation':True,'submitted':False,'nextUnit':None}
    cp = p.film.store.checkpoint(run_id)
    unit = next(u for u in cp.units if (u.scene_id,u.shot_id)==(target['sceneId'],target['shotId']))
    package = p.production_packages.get(unit.package_ref)
    bindings = ReferenceExecutionStore()
    ledger = PreviewLedger(p.ledger,bindings)
    operations = OperationResolver(p.creative_versions,ledger,p.operation_resolver.policy)
    reader = PackageReader(NativeCreativeSources(p.creative_versions,unit.refs,bindings),operations=operations)
    selection = await operations.select_unit(package,reader,phase_index=target['phaseIndex'],spoken_range=spoken_range)
    refs = select_references(p,run_id,unit,selection)
    binding_refs = tuple(bindings.register(b) for b in refs['candidates'])
    current = progress['currentUnit']
    previous = completion(p,current['runId']) if current else None
    base = previous[3].profile if previous else cp.operation_task.profile
    kind = target['boundary']
    if kind == 'CONTINUE':
        return {'simulation':True,'submitted':False,'nextUnit':target,'request':None,
            'reason':'A real official endpoint must be bound after the predecessor review. Use the existing continuation entry.',
            'references':refs['selected']}
    profile = resolve_profile(model=base.model,duration_ms=duration_ms or base.requested_duration_ms,
        resolution=base.resolution,ratio=base.aspect_ratio,native_audio=base.native_audio,
        policy=operations.policy,mode='reference' if binding_refs else 'text_to_video')
    # These explicit sentinels cannot pass normal admission. No decision is invented.
    sentinel = SourcePin(key='OFFLINE_PREVIEW_NOT_AUTHORIZED',kind='CANON',fingerprint='0'*64)
    decision = ArtifactReference(owner='user-decision',artifact_ref='OFFLINE_PREVIEW_NO_DECISION',version=1)
    adopted = next(p.creative_versions.resolve(r) for r in unit.refs if p.creative_versions.resolve(r).kind==Kind.SHOT)
    owners = OwnerBindings(adopted_refs=unit.refs,dpd_pin=sentinel,performance_scope_pin=sentinel,
        rights_pin=sentinel,rights_request_ref=ArtifactReference(owner='source-owner',artifact_ref=sentinel.key,version=1),
        rights_decision_ref=decision,adoption_decision_ref=adopted.adoption_decision_ref)
    boundary = MediaBoundary(kind=kind,predecessor_media_ref=previous[1].progress.video_ref,
        source_ref=package.scope.shot.model_copy(update={'path':('content','requiredTransition')})) if previous else None
    task = GenerationTask(target_model=profile.model,input_mode=profile.mode,native_audio='REQUIRED' if profile.native_audio else 'DISABLED',
        profile=profile,unit=selection,owners=owners,execution_reference_refs=binding_refs or None,return_last_frame=True,boundary=boundary)
    compiler = PromptCompiler(p.production_packages,p.generation_artifacts,reader,p.prompt_compiler.catalog,
        media_reader=RetainedMediaReader(p,progress['mediaIndex']))
    result = await compiler.preview_request(unit.package_ref,task)
    result.update(nextUnit=target,exitPreviousTailChain=True,references=refs['selected'],narrativeIdentitySources=refs['narrativeIdentitySources'],location=refs['location'],
        missingEvidence=refs['missingEvidence'],characterPackages=refs['characterPackages'],voice=refs['voice'],
        admission='NOT_RUN_NOT_AUTHORIZED',durationAuthority='Caller duration or inherited last execution profile for rehearsal only; not a per-phase timing rule.',
        sideEffects={'providerPosts':0,'audioCalls':0,'newChildren':0,'newReservations':0,'productionPreparations':0})
    return result
