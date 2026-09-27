"""Actual byte download projection; no provider calls or fabricated Media authority."""
import base64
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
import pytest
from drama_plugin.contracts.media import Media, MediaResolveResult, MediaType
from drama_plugin.hosts.http_video import VideoProviderHost
from drama_plugin.providers.video.image_delivery import decode_image_url, external_https
from test_official_video_providers import request, ref, with_refs, config

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')


class Store:
    def __init__(self) -> None:
        self.data = PNG
        self.record = Media(id='ref1',work_id='W',media_type=MediaType.IMAGE,source_ref='owned:job',purpose='VIDEO_INPUT',
            content_hash=hashlib.sha256(PNG).hexdigest(),file_size=len(PNG),mime_type='image/png',content={'reviewStatus':'PASS'})
        self.url='http://localhost/api/content/media/ref1';self.downloads=0;self.download_id='ref1'
    async def get_media(self, media_id: str) -> Media: return self.record
    async def resolve_media(self, media_id: str) -> MediaResolveResult:
        return MediaResolveResult(media_id='ref1',url=self.url,expires_at=datetime.now(timezone.utc)+timedelta(hours=1),mime_type=self.record.mime_type,size_bytes=len(self.data))
    async def download_media(self, media_id: str, destination: Path) -> MediaResolveResult:
        self.downloads+=1;destination.write_bytes(self.data)
        return (await self.resolve_media(media_id)).model_copy(update={'media_id':self.download_id})


async def prepared(tmp_path: Path, store: Store) -> tuple[Any, Any]:
    reference=ref().model_copy(update={'content_hash':hashlib.sha256(PNG).hexdigest()})
    r=with_refs(request(),[reference],input_mode='image_to_video',first_frame=reference)
    host=VideoProviderHost(None,store,None,tmp_path,configuration={'seedance':config('seedance')})
    provider=await host._provider('W',{'provider':'seedance','model':'seedance-2-mini','videoRequest':r.model_dump()},check_canon=False)
    return provider,r


async def test_internal_media_download_to_payload(tmp_path: Path) -> None:
    store=Store();p,r=await prepared(tmp_path,store)
    try:
        _,urls=await p.materialize(r)
        assert decode_image_url(urls['ref1'])==PNG and store.downloads==1
        payload=p.payload(r,urls,'attempt');wire=str(payload)
        assert 'data:image/png;base64,' in wire
        assert 'localhost' not in wire and 'interpretation' not in wire
    finally: await p.aclose()


@pytest.mark.parametrize('fault',['id','work','hash','failed','pending','bytes','mime','download_id'])
async def test_bad_reference_rejected(tmp_path: Path,fault: str) -> None:
    store=Store()
    changes={'id':{'id':'other'},'work':{'work_id':'OTHER'},'hash':{'content_hash':'a'*64},'failed':{'content':{'reviewStatus':'FAIL'}},'pending':{'content':{'reviewStatus':'PENDING'}},'mime':{'mime_type':'image/jpeg'}}
    if fault in changes:store.record=store.record.model_copy(update=changes[fault])
    if fault=='bytes':store.data=PNG[:-1]+b'x'
    if fault=='download_id':store.download_id='other'
    p,r=await prepared(tmp_path,store)
    try:
        with pytest.raises(ValueError): await p.materialize(r)
    finally: await p.aclose()


async def test_external_https_stays_direct(tmp_path: Path) -> None:
    store=Store();store.url='https://media.example.test/ref1.png';p,r=await prepared(tmp_path,store)
    try:
        _,urls=await p.materialize(r)
        assert urls['ref1']==store.url and store.downloads==0
    finally: await p.aclose()


@pytest.mark.parametrize('url',['https://localhost/x','https://127.0.0.1/x','https://[::1]/x','https://10.0.0.1/x','http://media.example/x'])
def test_internal_is_not_external_https(url: str) -> None:
    assert not external_https(url)


def test_malformed_data_rejected() -> None:
    with pytest.raises(ValueError): decode_image_url('data:image/png;base64,not-base64!')
    with pytest.raises(ValueError): decode_image_url('data:image/svg+xml;base64,'+base64.b64encode(b'<svg/>').decode())
