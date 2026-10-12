"""The storage queue is pointer-only and cannot retry a production operation."""
from pathlib import Path
import json
import pytest
from drama_plugin.film_storage.outbox import FilmOutbox
from drama_plugin.film_storage.storage import FilmStorage
from drama_plugin.film_storage.client import FilmStorageUnavailable


def test_same_event_survives_process_restart_without_payload_copy(tmp_path: Path):
    event={'kind':'LEDGER','type':'provider-receipt','workId':'w','ref':{'owner':'provider-receipt','artifactRef':'r','version':1}}
    queue=FilmOutbox(tmp_path/'queue');identity=queue.enqueue(event)
    original=json.loads((queue.path/(identity+'.json')).read_text())
    restored=FilmOutbox(queue.path)
    assert restored.enqueue(event)==identity
    assert restored.pending()==[(identity,original)]
    assert set(original)=={'event','sourceOrder','acknowledged'}
    restored.acknowledge(identity)
    assert queue.pending()==[]
    assert restored.enqueue(event)==identity and restored.pending()==[]


@pytest.mark.asyncio
async def test_one_unresolved_history_does_not_block_other_retained_events(tmp_path: Path):
    store=FilmStorage(object(),object(),tmp_path)
    calls=[]
    async def project(event,identity,order):
        calls.append(event['ref'])
        if event['ref']=='unavailable':raise FilmStorageUnavailable('retained pointer missing')
    store.project=project
    store.outbox.enqueue({'kind':'LEDGER','ref':'unavailable'})
    store.outbox.enqueue({'kind':'LEDGER','ref':'ready'})
    result=await store.flush()
    assert calls==['unavailable','ready']
    assert result['acknowledged']==1 and result['pending']==1
    assert result['doesNotAdvanceRuntime'] is True
    calls.clear()
    await store.flush()
    assert calls==['unavailable']


def test_current_owner_ledger_precedes_historical_archive_root(tmp_path: Path):
    import sqlite3
    from types import SimpleNamespace
    from drama_plugin.film_storage.projection import ledger_body, actual_wire
    native=tmp_path/'native.sqlite3';archive=tmp_path/'archive';archive.mkdir()
    for path,label in ((native,'current-owner'),(archive/'production.sqlite3','historical-archive')):
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE immutable_artifact(artifact_id TEXT, version INTEGER, artifact_type TEXT, body_json TEXT, work_id TEXT, scene_id TEXT, shot_id TEXT)')
            db.execute('INSERT INTO immutable_artifact VALUES (?,?,?,?,?,?,?)',('same-reference',1,'provider-attempt',json.dumps({'source':label}),'work','scene','shot'))
    store=SimpleNamespace(root=archive,plugin=SimpleNamespace(ledger=SimpleNamespace(path=native)))
    body,scope=ledger_body(store,{'owner':'provider-attempt','artifactRef':'same-reference','version':1})
    assert body=={'source':'current-owner'} and scope['workId']=='work'
    wire=native.with_name(native.name+'.receipts');wire.mkdir()
    (wire/'client.request.wire.json').write_text(json.dumps({'model':'actual-native-model','content':[]}))
    assert actual_wire(store,'client')['model']=='actual-native-model'


@pytest.mark.asyncio
async def test_superseded_requires_exact_existing_revision_slot(tmp_path: Path):
    import sqlite3
    from types import SimpleNamespace
    from drama_plugin.film_storage.projection import superseded_by_revision
    path=tmp_path/'production.sqlite3'
    scope={'workId':'work','sceneId':'scene','shotId':'shot'}
    op={'owner':'execution-operation','artifactRef':'replacement','version':1}
    revision={'owner':'film-segment-revision','artifactRef':'exact-revision','version':1}
    bodies=[('replacement','execution-operation',{'runId':'replacement-run'}),
      ('previous-operation','execution-operation',{'runId':'previous-run'}),
      ('exact-revision','film-segment-revision',{'replacementRunId':'replacement-run','previousRunId':'previous-run','slot':0,'previousCheckpoint':{'sceneMediaRunIds':['previous-run']}}),
      ('old-binding','media-binding',{'runId':'previous-run','operationRef':{'owner':'execution-operation','artifactRef':'previous-operation','version':1},'media':{'mediaId':'file'}})]
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE immutable_artifact(artifact_id TEXT,version INTEGER,artifact_type TEXT,body_json TEXT,work_id TEXT,scene_id TEXT,shot_id TEXT)')
        db.execute('CREATE TABLE ledger_index(index_type TEXT,index_key TEXT,value_json TEXT)')
        for identity,kind,body in bodies:db.execute('INSERT INTO immutable_artifact VALUES (?,?,?,?,?,?,?)',(identity,1,kind,json.dumps(body),'work','scene','shot'))
    class Client:
        def __init__(self):self.writes=[]
        async def query(self,table,filters,limit=30):
            if table=='drama_media':return [{'id':'file'}]
            return [{'id':'shot','take_no':1}]
        async def rows(self,rows):self.writes.extend(rows)
    client=Client();store=SimpleNamespace(root=tmp_path,client=client,row=FilmStorage.row)
    await superseded_by_revision(store,{'operationRef':op},'decision',1)
    assert client.writes==[]  # another adopted take alone does not replace anything
    with sqlite3.connect(path) as db:db.execute('INSERT INTO ledger_index VALUES (?,?,?)',('film-segment-dispatch-revision','replacement-run',json.dumps(revision)))
    await superseded_by_revision(store,{'operationRef':op},'decision',2)
    assert client.writes[0]['fields']['state']=='SUPERSEDED'
    assert client.writes[0]['fields']['take_no']==1
    assert 'exact-revision' in client.writes[0]['fields']['retention_reason']
