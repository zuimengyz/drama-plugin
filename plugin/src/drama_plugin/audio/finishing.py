"""Small local finishing adapter. No generation provider or artistic scoring."""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
from array import array
from pathlib import Path
from typing import Any

from drama_plugin.media_delivery import file_hash


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def run(args: list[str]) -> bytes:
    return subprocess.run(args, check=True, capture_output=True).stdout


def probe(path: Path) -> dict[str, Any]:
    return json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))


def video_packets(path: Path) -> list[dict[str, Any]]:
    return json.loads(run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_packets', '-show_data_hash', 'sha256', '-show_entries',
        'packet=pts_time,dts_time,duration_time,data_hash', '-of', 'json', str(path)]))['packets']


def number(value: Any) -> float:
    v = float(value)
    if not math.isfinite(v):
        raise ValueError('Non-finite timing/gain')
    return v


def envelope(points: list[list[float]]) -> str:
    """Piecewise linear gain; coordinates are local seconds after source trim."""
    if not points:
        raise ValueError('Explicit gain envelope required')
    pairs = [(number(t), number(g)) for t, g in points]
    if pairs[0][0] != 0 or any(g < 0 for _, g in pairs):
        raise ValueError('Gain begins at zero time and is nonnegative')
    if any(a[0] >= b[0] for a, b in zip(pairs, pairs[1:])):
        raise ValueError('Envelope times must increase')
    expression = f'{pairs[-1][1]:.9f}'
    for (a, ga), (b, gb) in reversed(list(zip(pairs, pairs[1:]))):
        expression = f'if(lt(t,{b:.9f}),{ga:.9f}+(t-{a:.9f})*{(gb-ga)/(b-a):.9f},{expression})'
    return expression


def render(recipe: dict[str, Any], paths: dict[str, str], directory: Path) -> dict[str, Any]:
    """Render deterministic local recipe; paths are disposable, IDs/hashes authoritative."""
    directory.mkdir(parents=True, exist_ok=True)
    fingerprint = digest(recipe)
    journal = directory / 'render.json'
    if journal.exists():
        old = json.loads(journal.read_text())
        if old['recipeHash'] != fingerprint:
            raise ValueError('Existing output belongs to a different recipe; use a new revision directory')
        if file_hash(Path(old['output'])) == old['outputHash']:
            return old
        raise ValueError('Retained local output changed; recover it before rendering again')
    source_id = recipe['sourceMediaId']
    expected = {**recipe['sources'], source_id: recipe['sourceHash']}
    verified: dict[str, Path] = {}
    probes: dict[str, Any] = {}
    for media_id, sha in expected.items():
        if media_id not in paths or not Path(paths[media_id]).is_file():
            raise ValueError(f'Missing source {media_id}; recover formal Media, no generation fallback')
        path = Path(paths[media_id])
        if file_hash(path) != sha:
            raise ValueError(f'Source hash mismatch: {media_id}')
        verified[media_id] = path
        probes[media_id] = probe(path)
    source = verified[source_id]
    duration = number(probes[source_id]['format']['duration'])
    bgm = recipe['soundPlan']['bgm']
    if bgm['decision'] not in {'NO_BGM', 'SUBTLE', 'ACTIVE'}:
        raise ValueError('Unknown BGM decision')
    if not bgm.get('purpose'):
        raise ValueError('BGM decision requires its dramatic reason, including NO_BGM')
    if bgm.get('sourceKind') == 'GENERATED':
        raise ValueError('GENERATED is an unavailable future seam, not a fallback')
    layers = recipe.get('layers', [])
    if bgm['decision'] == 'NO_BGM' and any(x.get('role') == 'BGM' for x in layers):
        raise ValueError('NO_BGM conflicts with a music layer')
    patches = recipe.get('patches', [])
    prior_end = 0.0
    for p in patches:
        a, b, fade = map(number, (p['start'], p['end'], p['fade']))
        if not 0 <= a < b <= duration or a < prior_end or not 0 < fade <= (b-a)/2:
            raise ValueError('Invalid or overlapping replacement window')
        if not p.get('evidence'):
            raise ValueError('Localized repair requires evidence')
        if any(a < number(d[1]) and b > number(d[0]) for d in recipe['protectedDialogue']):
            raise ValueError('Mixed-track replacement overlaps protected dialogue')
        prior_end = b
    def source_range(item: dict[str, Any], length: float) -> None:
        media_id = item['mediaId']
        start = number(item['sourceStart'])
        if media_id not in verified:
            raise ValueError(f'Missing verified donor {media_id}')
        audio = next((s for s in probes[media_id]['streams'] if s['codec_type'] == 'audio'), None)
        if audio is None or not 0 <= start < start+length <= number(audio.get('duration', probes[media_id]['format']['duration'])) + .001:
            raise ValueError('Donor range exceeds actual audio; no loop or padding fallback')
    for p in patches:
        source_range(p, number(p['end'])-number(p['start']))
    for layer in layers:
        length, start = number(layer['duration']), number(layer['start'])
        if length <= 0 or start < 0 or start+length > duration+.001:
            raise ValueError('Layer outside assembly')
        source_range(layer, length)
        envelope(layer['gain'])
        if number(layer['gain'][-1][0]) > length:
            raise ValueError('Envelope exceeds layer')
        if layer.get('lowpassHz') is not None and not 20 <= number(layer['lowpassHz']) <= 20000:
            raise ValueError('Invalid lowpass')
    ids = list(verified)
    args = ['ffmpeg', '-v', 'error', '-y']
    for media_id in ids:
        args += ['-i', str(verified[media_id])]
    filters: list[str] = []
    base_gain = '1'
    for p in patches:
        a, b, f = map(number, (p['start'], p['end'], p['fade']))
        gain = f'if(lt(t,{a}),1,if(lt(t,{a+f}),1-(t-{a})/{f},if(lt(t,{b-f}),0,if(lt(t,{b}),(t-{b-f})/{f},1))))'
        base_gain += f'*({gain})'
    # Honor shortened AAC packet durations at edit joins. Merely concatenating
    # decoded samples accumulates priming overlap and shifts later dialogue.
    filters.append(f"[{ids.index(source_id)}:a:0]aresample=48000:async=1:min_hard_comp=0.0001:first_pts=0,aformat=channel_layouts=stereo,volume='{base_gain}':eval=frame,apad,atrim=duration={duration}[base]")
    labels = ['[base]']
    for i, p in enumerate(patches):
        a,b,f = map(number,(p['start'],p['end'],p['fade']))
        length=b-a
        g=number(p.get('gain',1))
        if g < 0:
            raise ValueError('Negative patch gain')
        chain = f"[{ids.index(p['mediaId'])}:a:0]atrim=start={number(p['sourceStart'])}:duration={length},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,volume={g},afade=t=in:d={f},afade=t=out:st={length-f}:d={f},adelay={round(a*48000)}S:all=1[p{i}]"
        filters.append(chain); labels.append(f'[p{i}]')
    for i, layer in enumerate(layers):
        start, length = number(layer['start']), number(layer['duration'])
        lowpass = f",lowpass=f={number(layer['lowpassHz'])}" if layer.get('lowpassHz') else ''
        filters.append(f"[{ids.index(layer['mediaId'])}:a:0]atrim=start={number(layer['sourceStart'])}:duration={length},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo{lowpass},volume='{envelope(layer['gain'])}':eval=frame,adelay={round(start*48000)}S:all=1[l{i}]")
        labels.append(f'[l{i}]')
    filters.append(''.join(labels)+f'amix=inputs={len(labels)}:normalize=0:duration=first,atrim=duration={duration}[mix]')
    graph=';\n'.join(filters)
    graph_path=directory/'mix.ffgraph'; graph_path.write_text(graph)
    mix=directory/'mix.wav'
    command=args+['-filter_complex',graph,'-map','[mix]','-c:a','pcm_f32le',str(mix)]
    run(command)
    samples=array('f');samples.frombytes(run(['ffmpeg','-v','error','-i',str(mix),'-f','f32le','-']))
    peak=max((abs(x) for x in samples),default=0)
    if not math.isfinite(peak) or peak >= 1:
        raise ValueError(f'Mix clips or is invalid ({peak}); adjust the responsible layer')
    output=directory/'finished.mp4'
    mux=['ffmpeg','-v','error','-y','-copyts','-i',str(source),'-i',str(mix),
         '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k',
         '-avoid_negative_ts','disabled','-movflags','+faststart',str(output)]
    run(mux)
    before,after=video_packets(source),video_packets(output)
    if not before or before != after:
        raise ValueError('Video packets/timestamps changed; output not accepted')
    run(['ffmpeg','-v','error','-err_detect','explode','-i',str(output),'-f','null','-'])
    if file_hash(source) != recipe['sourceHash']:
        raise ValueError('Source mutated')
    result={'recipeHash':fingerprint,'sourceHash':recipe['sourceHash'],'output':str(output.resolve()),
        'outputHash':file_hash(output),'mixHash':file_hash(mix),'peakLinear':peak,
        'videoPacketsIdentical':True,'videoPacketCount':len(before),'videoPacketDigest':digest(before),
        'probe':probe(output),'commands':[command,mux],'generationCalls':0}
    journal.write_text(json.dumps(result,ensure_ascii=False,indent=2));return result


async def retain(session: Any, recipe: dict[str, Any], rendered: dict[str, Any], *, staging: Path, cache: Path) -> dict[str, Any]:
    """Reconcile the same revision through existing Media and Work/Scene contracts."""
    import shutil
    from drama_plugin.contracts.media import MediaType
    from drama_plugin.media_delivery import MediaIdentity, complete_retained_media
    fp=digest(recipe)
    if rendered['recipeHash'] != fp or not rendered['videoPacketsIdentical']:
        raise ValueError('Render/recipe mismatch')
    work=await session.memory.get_work(recipe['workId'])
    revisions=dict(work.content.get('finishingRevisions',{}))
    prior=revisions.get(recipe['revision'])
    if prior and prior['recipeHash'] != fp:
        raise ValueError('Finishing revision already sealed; preserve it and create a new revision')
    for media_id,sha in {**recipe['sources'],recipe['sourceMediaId']:recipe['sourceHash']}.items():
        m=await session.media.get_media(media_id)
        if m.work_id != work.id or m.content_hash != sha:
            raise ValueError('Formal source hash/ownership mismatch')
    scenes=[]
    for scene_id in recipe['sceneIds']:
        scene=await session.memory.get_scene(scene_id)
        episode=await session.memory.get_episode(scene.episode_id)
        script=await session.memory.get_script(episode.script_id)
        if script.work_id != work.id:
            raise ValueError('Scene belongs to another Work')
        scenes.append(scene)
    record={**(prior or {}),'recipeHash':fp,'recipe':recipe,'status':'PERSISTENCE_PENDING',
            'sourceMediaId':recipe['sourceMediaId'],'sourceHash':recipe['sourceHash'],
            'contentReview':recipe['review'],'userAdoption':'PENDING'}
    if prior is None:
        revisions[recipe['revision']]=record
        await session.memory.save_work(work.id,work.title,{**work.content,'finishingRevisions':revisions},work.description)
    source_ref=f"cinematic-finishing:{work.id}:{recipe['revision']}:{fp}"
    staging.mkdir(parents=True,exist_ok=True)
    staged=staging/f"{rendered['outputHash']}.mp4"
    if not staged.exists():shutil.copyfile(rendered['output'],staged)
    receipt=await complete_retained_media(session.media,session.memory,session.asset,
        MediaIdentity(work.id,MediaType.VIDEO,source_ref,rendered['outputHash'],purpose='CINEMATIC_FINISHING'),
        source=staged,content={**record,'videoPacketDigest':rendered['videoPacketDigest'],
        'videoPacketsIdentical':True,'generationCalls':0},cache=cache,target_id=recipe['revision'],
        content_review=recipe['review']['status'],user_adoption='PENDING',
        duration_ms=round(float(rendered['probe']['format']['duration'])*1000))
    # Merge fresh state after the shared business binding, never replace its write.
    work=await session.memory.get_work(work.id)
    revisions=dict(work.content.get('finishingRevisions',{}))
    durable={k:v for k,v in receipt.items() if k not in {'cachePath'}}
    record.update(status='CANDIDATE_SAVED',delivery=durable)
    revisions[recipe['revision']]=record
    if work.content.get('finishingRevisions') != revisions:
        await session.memory.save_work(work.id,work.title,{**work.content,'finishingRevisions':revisions},work.description)
    ref={'workId':work.id,'revision':recipe['revision'],'recipeHash':fp,
         'sourceMediaId':recipe['sourceMediaId'],'derivedMediaId':receipt['mediaId']}
    for scene in scenes:
        scene=await session.memory.get_scene(scene.id)
        refs=list(scene.content.get('finishingReferences',[]))
        if ref not in refs:
            await session.memory.save_scene(scene.id,scene.order,scene.title,
                {**scene.content,'finishingReferences':[*refs,ref]},scene.location)
        check=await session.memory.get_scene(scene.id)
        if check.content['finishingReferences'].count(ref) != 1:
            raise ValueError('Scene finishing reference readback mismatch')
    final=await session.memory.get_work(work.id)
    if final.content['finishingRevisions'][recipe['revision']] != record:
        raise ValueError('Finishing Work readback mismatch')
    return {**receipt,'workRevisionVerified':True,'sceneReferencesVerified':True}
