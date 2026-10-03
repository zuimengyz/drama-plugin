"""Eight-process Source→Film shadow; deterministic fixtures, zero live submission."""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from test_film_engine import Authors, Recipes, Reviewer, REF
from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.creative_engine.contracts import SourceBody, SceneBody, WorkBody, ScriptBody
from drama_plugin.film.contracts import FilmCanon, CanonScene, LanguageMetadata, DeliveryProfile, FinalFilmCandidate, FinalDelivery
from drama_plugin.execution.audio import ApprovedAudioConsumer
from drama_plugin.execution.review import MockReviewer
from drama_plugin.execution.contracts import ProviderResult
from drama_plugin.execution.transport import ReplayTransport
from drama_plugin.runtime.contracts import RuntimeState
SOURCE=Path('/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/source/designated-source.txt')

class SourceAuthors(Authors):
    async def author_film(self,request):
        self.calls.append('film-canon')
        if not request.source.text or 'ridiculous' not in request.source.text.lower():
            raise ValueError('Designated source required')
        return FilmCanon(work=WorkBody(interpretation='Remembered suffering contradicts declared indifference.',
            dramatic_intent='Follow a refused appeal into the room where it remains troubling.',character_meaning='The narrator cannot erase the child from his concern.'),
            script=ScriptBody(screenplay='The street encounter ends in refusal. In the room, the remembered encounter unsettles the narrator.'),
            scenes=(CanonScene(scene_id='street-encounter',scene=SceneBody(scene_text='A child asks for help; the narrator turns away.')),
                CanonScene(scene_id='room-memory',scene=SceneBody(scene_text='Back in his room, the narrator cannot dismiss the memory of the child.'))))

def guard(sock,address):
    if sock.family!=socket.AF_UNIX:
        raise AssertionError('E3-A permits no external network')
    return ORIGINAL_CONNECT(sock,address)
ORIGINAL_CONNECT=socket.socket.connect

async def phase(directory:Path,number:int)->None:
    import drama_plugin.plugin as module
    module.load_config=lambda _:DramaPluginConfig()
    socket.socket.connect=guard
    from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
    from drama_plugin.hosts.creative_source import CreativeSourceHost
    def forbidden(*args,**kwargs):
        raise AssertionError('No legacy author workflow or external agent tool selection')
    DirectorArtifactStore.transition=forbidden
    CreativeSourceHost.director_handoff=forbidden
    a=SourceAuthors()
    video=directory/'recorded-fixture.mp4'
    p=DramaPlugin.load(mock_data=MockDramaData(),ledger_path=directory/'ledger.sqlite',creative_root=directory/'creative',target_media_root=directory/'media',
        canon_author=a,direction_author=a,professional_author=a,film_canon_author=a,film_direction_author=a,
        film_recipes=Recipes(),film_reviewer=Reviewer(),target_reviewer=MockReviewer(),target_audio=ApprovedAudioConsumer(),
        target_transports={'offline-replay':ReplayTransport(directory/'remote',ProviderResult(result_id='offline-film-fixture',locator=str(video),expected_hash=hashlib.sha256(video.read_bytes()).hexdigest()))})
    stop={0:'film.canon:v1',1:'film.prepare:v1',2:'execution.provider:v1',3:'execution.media_intake:v1',4:'execution.media_review:v1',5:'film.assemble:v1'}.get(number)
    execute=p.runtime.executor.execute
    async def interrupted(key,inputs):
        result=await execute(key,inputs)
        if key==stop and result.status.value=='SUCCEEDED':
            (directory/f'phase-{number}.json').write_text(json.dumps({'phase':number,'interrupted_after':key,'run_id':inputs.run_id,'author_calls':a.calls},ensure_ascii=False,indent=2))
            os._exit(73)
        return result
    p.runtime.executor.execute=interrupted
    if number==0:
        source=SOURCE.read_text()
        p.create_source_film_run(work_id='source-film-shadow',run_id='film-shadow',source=SourceBody(goal='Bounded source film segment through final candidate',text=source,spoken_language='ru'),
            languages=LanguageMetadata(source_document_language='en',original_work_language='ru',spoken_language='ru',authority_ref=REF),
            profile=DeliveryProfile(width=160,height=90),rights_refs=(REF,),route='offline-replay',model='seedance-2-standard')
        await p.runtime.run('film-shadow')
    elif number==2:
        run=await p.resume_source_film_run('film-shadow')
        assert run.state==RuntimeState.WAITING_USER
        cp=p.film.store.checkpoint(run.run_id)
        await p.decide_target_run(run.run_id,decision_id=p.runtime.decision_id(run.run_id),accepted=True,source_ref=cp.plan_ref)
        await p.runtime.run(run.run_id)
        await p.resume_source_film_run(run.run_id)
    elif number==7:
        run=await p.resume_source_film_run('film-shadow')
        assert run.state==RuntimeState.WAITING_USER
        cp=p.film.store.checkpoint(run.run_id)
        before=p.runtime.decision_id(run.run_id)
        assert before==json.loads((directory/'phase-6.json').read_text())['decision_id']
        await p.decide_target_run(run.run_id,decision_id=before,accepted=True,source_ref=cp.final_ref)
        run=await p.runtime.run(run.run_id)
        assert run.state==RuntimeState.SUCCEEDED,run
        cp=p.film.store.checkpoint(run.run_id)
        final=p.film.store.get(cp.final_ref,FinalFilmCandidate)
        delivery=p.film.store.get(cp.delivery_ref,FinalDelivery)
        summary={'phase':number,'state':run.state.value,'scenes':len({u.scene_id for u in cp.units}),'shots':len(cp.units),
            'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'final_candidate':final.model_dump(mode='json',by_alias=True),
            'delivery':delivery.model_dump(mode='json',by_alias=True),'author_calls':a.calls,
            'offline_logical_operations':len((directory/'remote'/'submissions.jsonl').read_text().splitlines()),
            'runtime_checkpoint_bytes':len(p.runtime.serialize(run.run_id).encode()),'film_checkpoint_bytes':len(cp.model_dump_json().encode()),
            'EXTERNAL_AGENT_INTERNAL_TOOL_SELECTION':0,'REAL_PROVIDER_SUBMISSION':0,'PAID_GENERATION_CALLS':0,'LIVE_MEDIA_GENERATION':0,
            'CREATIVE_QUALITY_LIVE_ACCEPTED':False,'FINAL_ACCEPTANCE_KIND':'SYNTHETIC_OFFLINE_FIXTURE'}
        (directory/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    else:
        run=await p.resume_source_film_run('film-shadow')
        if number==6:
            assert run.state==RuntimeState.WAITING_USER,run
            cp=p.film.store.checkpoint(run.run_id)
            (directory/'phase-6.json').write_text(json.dumps({'phase':number,'state':run.state.value,'decision_id':p.runtime.decision_id(run.run_id),
                'final_ref':cp.final_ref.model_dump(mode='json'),'author_calls':a.calls},ensure_ascii=False,indent=2))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--phase',type=int)
    args=parser.parse_args()
    directory=args.directory.resolve();directory.mkdir(parents=True,exist_ok=True)
    if args.phase is not None:
        asyncio.run(phase(directory,args.phase));return
    video=directory/'recorded-fixture.mp4'
    subprocess.run(['ffmpeg','-nostdin','-v','error','-f','lavfi','-i','color=c=black:s=160x90:r=24:d=4','-f','lavfi','-i','sine=frequency=220:duration=4',
        '-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest','-y',str(video)],check=True)
    for number in range(8):
        completed=subprocess.run([sys.executable,__file__,'--directory',str(directory),'--phase',str(number)],capture_output=True,text=True,timeout=180)
        if completed.returncode!=(73 if number<6 else 0):
            raise RuntimeError(f'Phase {number} failed: {completed.stdout}\n{completed.stderr}')
    print(json.dumps({'shadow':'PASS','processes':8,'summary':str(directory/'summary.json')},ensure_ascii=False))
if __name__=='__main__':
    main()
