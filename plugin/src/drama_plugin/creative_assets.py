"""Host helpers over the existing Asset/Media Tool registry, never a new service."""
from __future__ import annotations

from typing import Any
from pathlib import Path

from drama_plugin.contracts.asset import Asset, AssetType
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.creative_asset import (
    BgmContent, BgmSelection, CinematicLanguageContent, CinematicLanguageRef,
)
from drama_plugin.contracts.media import Media, MediaType
from drama_plugin.tools.registry import ToolRegistry
from drama_plugin.providers.base.interfaces import MediaProvider


async def retain_bgm_media(tools: ToolRegistry, provider: MediaProvider, *, work_id: str,
                           source: Path, original_source: str, cache: Path) -> Media:
    """Retain a Host-confirmed existing project source, reusing bytes across renames.

    This does not establish copyright or production eligibility. No generation.
    A saturated legacy listing blocks ambiguous imports instead of creating duplicates.
    """
    from drama_plugin.audio.host_media import probe_media
    from drama_plugin.media_delivery import file_hash, verify_media, MediaIdentity
    digest = file_hash(source)
    stable = f'bgm:{work_id}:sha256:{digest}'
    exact = await tools.invoke('media.list_media', work_id=work_id, media_type=MediaType.AUDIO,
                               source_ref=stable, include_debug=True)
    candidates = exact or await tools.invoke('media.list_media', work_id=work_id,
                                             media_type=MediaType.AUDIO, include_debug=True)
    matches = [m for m in candidates if m.content_hash == digest]
    if len(matches) > 1:
        raise ValueError('Ambiguous existing BGM physical identity; reconcile before import')
    if exact and not matches:
        raise ValueError('BGM stable source has conflicting bytes')
    if matches:
        media: Media = matches[0]
    else:
        if len(candidates) >= 100:
            raise ValueError('Media listing saturated; cannot prove absence before import')
        physical = probe_media(source)
        if not any(s.get('codec_type') == 'audio' for s in physical.streams) or any(
                s.get('codec_type') == 'video' for s in physical.streams):
            raise ValueError('BGM source must be standalone audio')
        media = await tools.invoke('media.import_media', work_id=work_id, media_type=MediaType.AUDIO,
            source_uri=source.resolve().as_uri(), source_ref=stable, duration_ms=physical.duration_ms,
            purpose='BGM', content={'originalSource': original_source})
    if media.work_id != work_id or media.media_type != MediaType.AUDIO or media.content_hash != digest:
        raise ValueError('BGM imported/reused identity mismatch')
    await verify_media(provider, MediaIdentity.from_media(media), cache)
    return media


async def remember(tools: ToolRegistry, work_id: str,
                   content: CinematicLanguageContent | BgmContent) -> tuple[Asset, str]:
    """Search before create; mismatching revisions require explicit review, never overwrite.

    The service serializes same-work creative creates. After an uncertain write,
    rerun this operation to reconcile the same key/hash before attempting a write.
    """
    raw = dump_contract(content)
    is_language = isinstance(content, CinematicLanguageContent)
    kind = AssetType.OTHER if is_language else AssetType.AUDIO_INPUT
    if isinstance(content, CinematicLanguageContent):
        key = content.semantic_key
    else:
        if not content.media:
            raise ValueError('Formal BGM registration requires existing Media identity')
        key = content.media.content_hash
        await verified_music_identity(tools, work_id, content)
    candidates = await tools.invoke('asset.search_assets', query=key, asset_type=kind)
    matches = [a for a in candidates if a.work_id == work_id and (
        a.content.get('semanticKey') == key if is_language else
        a.content.get('creativeKind') == 'MUSIC' and a.content.get('role') == 'BGM'
        and a.content.get('media', {}).get('contentHash') == key)]
    if len(matches) > 1:
        raise ValueError('Ambiguous existing creative identity; reconcile duplicates')
    if matches:
        asset = await tools.invoke('asset.get_asset', asset_id=matches[0].id)
        if asset.content != raw:
            raise ValueError('Creative asset revision conflict; existing content preserved')
        return asset, 'REUSED'
    refs = [content.media.media_id] if isinstance(content, BgmContent) and content.media else []
    asset = await tools.invoke('asset.create_asset', work_id=work_id, asset_type=kind,
        name=content.title, content=raw, reference_media_ids=refs)
    read = await tools.invoke('asset.get_asset', asset_id=asset.id)
    found = await tools.invoke('asset.search_assets', query=key, asset_type=kind)
    if read.content != raw or read.id not in {a.id for a in found}:
        raise ValueError('Creative asset readback/search mismatch')
    return read, 'CREATED'


async def search_patterns(tools: ToolRegistry, query: str) -> list[dict[str, Any]]:
    """Keyword retrieval with explicit evidence; Host judges applicability, including zero."""
    results = []
    for asset in await tools.invoke('asset.search_assets', query=query, asset_type=AssetType.OTHER):
        if asset.content.get('creativeKind') != 'CINEMATIC_LANGUAGE':
            continue
        c = CinematicLanguageContent.model_validate(asset.content)
        if c.validation.status == 'REJECTED':
            continue
        results.append({'asset': dump_contract(asset), 'contentFingerprint': sha256_canonical(asset.content),
            'matchReason': {'query': query, 'purpose': c.purpose, 'tags': list(c.tags),
                            'suitableFor': list(c.suitable_for)}})
    return results


def pattern_ref(asset: Asset, applied_purpose: str) -> CinematicLanguageRef:
    c = CinematicLanguageContent.model_validate(asset.content)
    if c.validation.status == 'REJECTED':
        raise ValueError('Rejected pattern cannot be adopted')
    return CinematicLanguageRef(asset_id=asset.id,
        content_fingerprint=sha256_canonical(asset.content), applied_purpose=applied_purpose)


async def verified_music_identity(tools: ToolRegistry, work_id: str, music: BgmContent) -> Media:
    if not music.media:
        raise ValueError('Missing BGM Media')
    m: Media = await tools.invoke('media.get_media', media_id=music.media.media_id)
    if (m.work_id != work_id or m.media_type != MediaType.AUDIO
            or (m.source_ref, m.content_hash) != (music.media.source_ref, music.media.content_hash)
            or not m.mime_type or not m.mime_type.startswith('audio/') or not m.file_size):
        raise ValueError('BGM Media scope/hash/type mismatch')
    if music.duration is not None and (not m.duration_ms or abs(m.duration_ms / 1000 - music.duration) > .001):
        raise ValueError('BGM duration differs from Media')
    return m  # Byte readback remains mandatory at retention/selection, not inferred here.


async def search_bgm(tools: ToolRegistry, decision: str, query: str = 'BGM', *,
                     production_only: bool = False, mood: str | None = None,
                     narrative_function: str | None = None) -> list[dict[str, Any]]:
    if decision == 'NO_BGM':
        return []
    if decision not in {'SUBTLE', 'ACTIVE'}:
        raise ValueError('Unknown BGM decision')
    results = []
    for asset in await tools.invoke('asset.search_assets', query=query, asset_type=AssetType.AUDIO_INPUT):
        if (asset.content.get('creativeKind'), asset.content.get('role')) != ('MUSIC', 'BGM'):
            continue
        c = BgmContent.model_validate(asset.content)
        if mood and mood.casefold() not in {x.casefold() for x in c.mood}:
            continue
        if narrative_function and narrative_function.casefold() not in {x.casefold() for x in c.narrative_functions}:
            continue
        eligible = c.production_eligible and c.rights.allows_production() and c.media is not None
        if production_only:
            if not eligible:
                continue
            await verified_music_identity(tools, asset.work_id, c)
        results.append({'asset': dump_contract(asset), 'productionEligible': eligible,
            'matchReason': {'query': query, 'mood': list(c.mood),
                'narrativeFunctions': list(c.narrative_functions), 'rightsStatus': c.rights.status}})
    return results


def select_bgm(asset: Asset, media: Media, *, decision: str, selected_range: tuple[float, float],
               reason: str) -> BgmSelection:
    """Explicit Host choice; full byte verification is performed by finishing before render."""
    c = BgmContent.model_validate(asset.content)
    if decision not in {'SUBTLE', 'ACTIVE'} or not c.production_eligible or not c.media:
        raise ValueError('BGM production selection blocked')
    if (not c.rights.allows_production() or media.media_type != MediaType.AUDIO
            or asset.work_id != media.work_id or media.id not in asset.reference_media_ids
            or (c.media.media_id, c.media.content_hash, c.media.source_ref) != (media.id, media.content_hash, media.source_ref)
            or not media.duration_ms or selected_range[1] > media.duration_ms / 1000):
        raise ValueError('BGM rights/Media/range mismatch')
    return BgmSelection(asset_id=asset.id, asset_fingerprint=sha256_canonical(asset.content),
        media_id=media.id, content_hash=c.media.content_hash, selected_range=selected_range, reason=reason)


def validate_music_recipe(recipe: dict[str, Any]) -> None:
    """Fail closed before cache lookup, probing or rendering any production BGM layer.

    Retain Asset and Media snapshots with the recipe for revision traceability. The
    Host refreshes rights through get_asset before authorizing a new production.
    """
    decision = recipe['soundPlan']['bgm']['decision']
    for layer in recipe.get('layers', []):
        if layer.get('role') != 'BGM':
            continue
        if not all(key in layer for key in ('bgmAsset', 'bgmMedia', 'bgmSelection')):
            raise ValueError('BGM requires rights and lineage snapshots before production')
        asset = Asset.model_validate(layer['bgmAsset'])
        media = Media.model_validate(layer['bgmMedia'])
        selected = BgmSelection.model_validate(layer['bgmSelection'])
        expected = select_bgm(asset, media, decision=decision,
            selected_range=(float(layer['sourceStart']), float(layer['sourceStart']) + float(layer['duration'])),
            reason=selected.reason)
        if (selected != expected or layer['mediaId'] != selected.media_id
                or recipe['sources'].get(selected.media_id) != selected.content_hash):
            raise ValueError('BGM lineage differs from executable layer')
