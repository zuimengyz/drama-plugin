"""Durable media completion. Generation, content review and adoption stay separate.

No generator is reachable from this module. Retrying completion can only recover
the same source identity, read back bytes and reconcile its business binding.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, TypeVar
from urllib.parse import urlsplit

import httpx

from drama_plugin.audio.host_media import probe_media
from drama_plugin.contracts.media import Media, MediaType
from drama_plugin.exceptions import RemoteServiceError
from drama_plugin.providers.base.interfaces import MediaProvider, MemoryProvider, AssetProvider

T = TypeVar("T")


class PersistenceError(ValueError):
    """Fail closed without changing generation, content or adoption facts."""


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


async def read_retry(operation: Callable[[], Awaitable[T]], *, refresh_expired: bool = False) -> T:
    for attempt in range(3):
        try:
            return await operation()
        except (RemoteServiceError, httpx.HTTPError) as exc:
            status = getattr(exc, "status_code", None)
            if isinstance(exc, httpx.HTTPStatusError):
                status = exc.response.status_code
            code = getattr(exc, "error_code", None)
            expired = refresh_expired and status in (401, 403) and attempt == 0
            if code in {"CONTENT_HASH_MISMATCH", "CONFLICT", "OBJECT_CONFLICT", "UNAUTHORIZED"}:
                raise
            if attempt == 2 or (status not in (None, 408, 429, 500, 502, 503, 504) and not expired):
                raise
            await asyncio.sleep(0.1 * 2**attempt)
    raise AssertionError("unreachable")


@dataclass(frozen=True)
class MediaIdentity:
    work_id: str
    media_type: MediaType
    source_ref: str
    content_hash: str
    shot_id: str | None = None
    asset_id: str | None = None
    purpose: str | None = None
    media_id: str | None = None

    @classmethod
    def from_media(cls, media: Media) -> MediaIdentity:
        return cls(media.work_id, media.media_type, media.source_ref, media.content_hash or "",
                   media.shot_id, media.asset_id, media.purpose, media.id)

    def check(self, media: Media) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", self.content_hash) or not self.source_ref:
            raise PersistenceError("Stable source and complete SHA-256 required")
        for field in ("work_id", "media_type", "source_ref", "content_hash", "shot_id", "asset_id", "purpose"):
            if getattr(media, field) != getattr(self, field):
                raise PersistenceError(f"Media identity mismatch: {field}")
        if self.media_id and media.id != self.media_id:
            raise PersistenceError("Selected Media version changed")
        if not media.file_size or not media.mime_type:
            raise PersistenceError("Physical Media metadata is incomplete")


def inspect_bytes(path: Path, media_type: MediaType) -> dict[str, Any]:
    # ffprobe decodes image headers and audio/video streams without rewriting bytes.
    if media_type == MediaType.IMAGE:
        import subprocess
        import json
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
                                 "-of", "json", str(path)], check=True, capture_output=True, text=True)
        streams = json.loads(result.stdout).get("streams", [])
        if not any(s.get("width", 0) > 0 and s.get("height", 0) > 0 for s in streams):
            raise PersistenceError("Image cannot be decoded")
        subprocess.run(["ffmpeg", "-v", "error", "-err_detect", "explode", "-i", str(path),
                        "-frames:v", "1", "-f", "null", "-"], check=True, capture_output=True)
        return {"implementation": "ffprobe+ffmpeg-image-decode", "streams": streams}
    probed = probe_media(path)
    kind = "video" if media_type == MediaType.VIDEO else "audio"
    if not any(s.get("codec_type") == kind for s in probed.streams):
        raise PersistenceError(f"Missing {kind} stream")
    return {"implementation": probed.implementation, "durationMs": probed.duration_ms,
            "streams": list(probed.streams)}


async def verify_media(provider: MediaProvider, expected: MediaIdentity, cache: Path) -> dict[str, Any]:
    if not expected.media_id:
        raise PersistenceError("A local file is not a stable Media reference")
    record = await read_retry(lambda: provider.get_media(expected.media_id or ""))
    expected.check(record)
    cache.mkdir(parents=True, exist_ok=True)
    # Never accept a prior cache as evidence that the formal object still exists.
    suffix = {MediaType.IMAGE: ".img", MediaType.VIDEO: ".mp4", MediaType.AUDIO: ".audio"}[record.media_type]
    with tempfile.NamedTemporaryFile(dir=cache, suffix=suffix, delete=False) as handle:
        downloaded = Path(handle.name)
    try:
        # download_media resolves afresh on every retry, including expired delivery URLs.
        resolved = await read_retry(lambda: provider.download_media(record.id, downloaded), refresh_expired=True)
        if resolved.media_id != record.id or downloaded.stat().st_size != record.file_size:
            raise PersistenceError("Formal readback identity/size mismatch")
        if file_hash(downloaded) != expected.content_hash:
            raise PersistenceError("Formal readback SHA-256 mismatch")
        physical = inspect_bytes(downloaded, record.media_type)
        destination = cache / f"{record.id}-{expected.content_hash}{suffix}"
        downloaded.replace(destination)
        location = urlsplit(resolved.url)
        return {"persistenceStatus": "VERIFIED", "mediaId": record.id, "sourceRef": record.source_ref,
                "contentHash": expected.content_hash, "sizeBytes": record.file_size,
                "workId": record.work_id, "shotId": record.shot_id, "assetId": record.asset_id,
                "purpose": record.purpose, "mediaType": record.media_type.value,
                "storageDelivery": {"scheme": location.scheme, "host": location.hostname,
                                    "path": location.path, "signedQuerySaved": False},
                "cachePath": str(destination.resolve()), "technical": physical}
    finally:
        downloaded.unlink(missing_ok=True)


async def persist_media(provider: MediaProvider, expected: MediaIdentity, *, source: Path,
                        content: dict[str, Any], cache: Path, duration_ms: int | None = None) -> dict[str, Any]:
    if file_hash(source) != expected.content_hash:
        raise PersistenceError("Staging source hash changed")
    inspect_bytes(source, expected.media_type)

    async def find() -> list[Media]:
        return await provider.list_media(work_id=expected.work_id, media_type=expected.media_type,
                                         source_ref=expected.source_ref, purpose=expected.purpose, include_debug=True)

    if expected.media_id:
        record = await read_retry(lambda: provider.get_media(expected.media_id or ""))
    else:
        matches = await read_retry(find)
        if len(matches) > 1:
            raise PersistenceError("Ambiguous source identity; reconcile before importing")
        if matches:
            record = matches[0]
        else:
            try:
                record = await provider.import_media(work_id=expected.work_id, media_type=expected.media_type,
                    source_uri=source.resolve().as_uri(), content=content, shot_id=expected.shot_id,
                    asset_id=expected.asset_id, purpose=expected.purpose, source_ref=expected.source_ref,
                    duration_ms=duration_ms)
            except (RemoteServiceError, httpx.HTTPError):
                # A lost response is not permission to repeat the write, let alone generate.
                matches = await read_retry(find)
                if len(matches) != 1:
                    raise PersistenceError("Import outcome unresolved; recover the same source before retrying")
                record = matches[0]
    expected.check(record)
    return await verify_media(provider, MediaIdentity.from_media(record), cache)


async def bind_delivery(memory: MemoryProvider, asset: AssetProvider, receipt: dict[str, Any], *,
                        target_id: str, retention: str, content_review: str, user_adoption: str,
                        selection: dict[str, Any] | None = None) -> dict[str, Any]:
    if receipt.get("persistenceStatus") != "VERIFIED":
        raise PersistenceError("Business completion requires verified persistence")
    if retention not in {"FORMAL", "CANDIDATE"}:
        raise PersistenceError("Only retained media can enter formal completion")
    binding = {k: receipt[k] for k in ("mediaId", "sourceRef", "contentHash", "mediaType", "purpose")}
    binding.update(targetId=target_id, retention=retention, contentReview=content_review,
                   userAdoption=user_adoption)
    if selection:
        binding["selection"] = selection
    entity: Any
    if receipt.get("assetId"):
        entity = await asset.get_asset(receipt["assetId"])
        if entity.work_id != receipt["workId"]:
            raise PersistenceError("Asset belongs to another Work")
    elif receipt.get("shotId"):
        entity = await memory.get_shot(receipt["shotId"])
        scene = await memory.get_scene(entity.scene_id)
        episode = await memory.get_episode(scene.episode_id)
        script = await memory.get_script(episode.script_id)
        if script.work_id != receipt["workId"]:
            raise PersistenceError("Shot belongs to another Work")
    else:
        entity = await memory.get_work(receipt["workId"])
    content = dict(entity.content)
    bindings = list(content.get("mediaBindings", []))
    key = (target_id, receipt["purpose"], user_adoption)
    same = [b for b in bindings if (b.get("targetId"), b.get("purpose"), b.get("userAdoption")) == key]
    if same and same != [binding]:
        raise PersistenceError("Binding/version conflict; an explicit selection revision is required")
    if not same:
        content["mediaBindings"] = [*bindings, binding]
        if receipt.get("assetId"):
            refs = list(dict.fromkeys([*entity.reference_media_ids, receipt["mediaId"]]))
            await asset.save_asset(entity.id, entity.name, content, entity.description, refs)
        elif receipt.get("shotId"):
            await memory.save_shot(entity.id, entity.shot_no, content, entity.title, entity.shot_type)
        else:
            await memory.save_work(entity.id, entity.title, content, entity.description)
    reread: Any
    if receipt.get("assetId"):
        reread = await asset.get_asset(entity.id)
    elif receipt.get("shotId"):
        reread = await memory.get_shot(entity.id)
    else:
        reread = await memory.get_work(entity.id)
    if reread.content.get("mediaBindings", []).count(binding) != 1:
        raise PersistenceError("Business binding readback mismatch")
    return {**receipt, "bindingStatus": "VERIFIED", "bindingEntityId": entity.id,
            "binding": binding, "deliveryStatus": "READY" if retention == "FORMAL" else "CANDIDATE_SAVED"}


async def complete_retained_media(provider: MediaProvider, memory: MemoryProvider, asset: AssetProvider,
                                  expected: MediaIdentity, *, source: Path | None, content: dict[str, Any],
                                  cache: Path, target_id: str, retention: str = 'CANDIDATE',
                                  content_review: str = 'PENDING_REVIEW', user_adoption: str = 'PENDING',
                                  selection: dict[str, Any] | None = None,
                                  duration_ms: int | None = None) -> dict[str, Any]:
    receipt = (await persist_media(provider, expected, source=source, content=content, cache=cache,
                                  duration_ms=duration_ms) if source is not None else
               await verify_media(provider, expected, cache))
    return await bind_delivery(memory, asset, receipt, target_id=target_id, retention=retention,
                               content_review=content_review, user_adoption=user_adoption, selection=selection)


async def prepare_bound_media(provider: MediaProvider, memory: MemoryProvider, *, shot_id: str,
                              target_id: str, cache: Path, adopted: bool = False) -> dict[str, Any]:
    shot = await read_retry(lambda: memory.get_shot(shot_id))
    bindings = [b for b in shot.content.get('mediaBindings', []) if b.get('targetId') == target_id
                and b.get('mediaType') == 'VIDEO' and
                (not adopted or b.get('userAdoption') == 'USER_SELECTED')]
    if len(bindings) != 1:
        raise PersistenceError('Exactly one current business media binding is required')
    binding = bindings[0]
    record = await read_retry(lambda: provider.get_media(binding['mediaId']))
    scene = await memory.get_scene(shot.scene_id)
    episode = await memory.get_episode(scene.episode_id)
    script = await memory.get_script(episode.script_id)
    if (record.shot_id != shot_id or record.work_id != script.work_id or
            record.content_hash != binding['contentHash'] or record.source_ref != binding['sourceRef'] or
            record.purpose != binding['purpose']):
        raise PersistenceError('Business selection and Media version/ownership mismatch')
    receipt = await verify_media(provider, MediaIdentity.from_media(record), cache)
    receipt.update(bindingStatus='VERIFIED', bindingEntityId=shot_id, binding=binding,
                   deliveryStatus='READY' if adopted else 'REVIEW_READY')
    if adopted:
        selection = binding.get('selection', {})
        if (selection.get('decision') != 'REUSE_SOURCE_AV' or
                selection.get('authority') != 'USER_EXPLICIT_ADOPTION' or
                selection.get('audioProcessing') != []):
            raise PersistenceError('Explicit unprocessed source AV adoption is required')
        from drama_plugin.audio.host_media import assemble_av
        from drama_plugin.contracts.audio import AvAssemblyManifest
        assembled = assemble_av(Path(receipt['cachePath']), manifest=AvAssemblyManifest(
            source_video_media_id=record.id, timeline=[]), source_video_hash=binding['contentHash'])
        return {**assembled, 'status':'READY', 'persistence':receipt, 'selection':selection,
                'generationCalls':0, 'additionalDubbingLineIds':[]}
    return receipt


async def assemble_av_delivery(provider: MediaProvider, memory: MemoryProvider, asset: AssetProvider, *,
                               source_identity: MediaIdentity, mix_identity: MediaIdentity,
                               manifest: Any, output: Path, source_ref: str, cache: Path,
                               target_id: str) -> dict[str, Any]:
    """Explicit derivative completion. A mux is local until this entry succeeds.

    A pending output journal belongs to the same assembly, not another generator
    or budget. Resume imported/staged bytes without remuxing. Native adoption uses
    prepare_bound_media instead and never reaches this function implicitly.
    """
    from drama_plugin.audio.host_media import assemble_av
    from drama_plugin.contracts.base import dump_contract, sha256_canonical
    import json
    if (source_identity.media_type != MediaType.VIDEO or mix_identity.media_type != MediaType.AUDIO
            or source_identity.work_id != mix_identity.work_id
            or manifest.source_video_media_id != source_identity.media_id
            or manifest.audio_mix_media_id != mix_identity.media_id):
        raise PersistenceError('Explicit source/mix manifest ownership mismatch')
    if source_identity.shot_id and mix_identity.shot_id not in (None, source_identity.shot_id):
        raise PersistenceError('Mix belongs to another Shot')
    fingerprint = sha256_canonical({'manifest':dump_contract(manifest), 'sourceHash':source_identity.content_hash,
                                    'mixHash':mix_identity.content_hash})
    content = {'assemblyFingerprint':fingerprint, 'manifest':dump_contract(manifest),
               'sourceVideoMediaId':source_identity.media_id, 'sourceVideoContentHash':source_identity.content_hash,
               'audioMixMediaId':mix_identity.media_id, 'audioMixContentHash':mix_identity.content_hash,
               'retention':'CANDIDATE', 'reviewStatus':'PENDING_REVIEW'}
    existing = await read_retry(lambda: provider.list_media(work_id=source_identity.work_id, source_ref=source_ref,
                                                           media_type=MediaType.VIDEO, include_debug=True))
    if existing:
        if len(existing) != 1 or existing[0].content.get('assemblyFingerprint') != fingerprint:
            raise PersistenceError('Assembly stable source conflict')
        result = existing[0]
        if result.work_id != source_identity.work_id or result.shot_id != source_identity.shot_id:
            raise PersistenceError('Assembly result ownership mismatch')
        return await complete_retained_media(provider,memory,asset,MediaIdentity.from_media(result),
            source=None,content=content,cache=cache,target_id=target_id)
    journal = output.with_suffix(output.suffix + '.delivery.json')
    if output.exists():
        if not journal.exists():
            raise PersistenceError('Unidentified existing assembly output; never overwrite')
        saved = json.loads(journal.read_text())
        if saved['assemblyFingerprint'] != fingerprint or saved['contentHash'] != file_hash(output):
            raise PersistenceError('Staged assembly identity/hash conflict')
    else:
        source = await verify_media(provider,source_identity,cache/'source')
        mix = await verify_media(provider,mix_identity,cache/'mix')
        output.parent.mkdir(parents=True,exist_ok=True)
        assemble_av(Path(source['cachePath']),manifest=manifest,source_video_hash=source_identity.content_hash,
            audio_mix=Path(mix['cachePath']),audio_mix_hash=mix_identity.content_hash,output=output)
        journal.write_text(json.dumps({'assemblyFingerprint':fingerprint,'contentHash':file_hash(output)}))
    identity = MediaIdentity(source_identity.work_id,MediaType.VIDEO,source_ref,file_hash(output),
                             shot_id=source_identity.shot_id,purpose='FINAL_AV_CANDIDATE')
    return await complete_retained_media(provider,memory,asset,identity,source=output,content=content,
        cache=cache/'output',target_id=target_id,duration_ms=probe_media(output).duration_ms)
