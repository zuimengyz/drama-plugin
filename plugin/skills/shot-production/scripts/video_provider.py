#!/usr/bin/env python3
"""Official video lifecycle on an existing formal route and reserved attempt."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src'))
from drama_plugin.hosts.http_video import VideoProviderHost, cost_metrics
from drama_plugin.hosts.mcp_media import McpMediaSession
from drama_plugin.providers.video.registry import settings, model_availability


async def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['status','models','bind','submit','poll','metrics'])
    p.add_argument('--mcp-config', type=Path)
    p.add_argument('--work-id')
    p.add_argument('--attempt-id')
    p.add_argument('--decision', type=Path)
    p.add_argument('--cache', type=Path)
    a = p.parse_args()
    if a.command == 'models':
        print(json.dumps(model_availability(), ensure_ascii=False, indent=2))
        return
    if a.command == 'status':
        print(json.dumps({k:v.status(k) for k,v in settings().items()} | {'comfy_cloud':'MCP_DISCOVERY_REQUIRED'}))
        return
    if not a.mcp_config or not a.work_id or not a.cache:
        p.error('--mcp-config, --work-id and --cache required')
    a.cache.mkdir(parents=True, exist_ok=True)
    lock = a.cache / (a.work_id + '.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        async with McpMediaSession(a.mcp_config) as s:
            h = VideoProviderHost(s.memory,s.media,s.asset,a.cache)
            if a.command == 'bind':
                if not a.decision: p.error('--decision required')
                result = await h.bind(a.work_id,json.loads(a.decision.read_text()))
            elif a.command == 'metrics':
                work = await s.memory.get_work(a.work_id)
                result = cost_metrics(work.content['productionStage']['attempts'])
            else:
                if not a.attempt_id: p.error('--attempt-id required')
                result = (await getattr(h,a.command)(a.work_id,a.attempt_id)).durable()
            print(json.dumps(result,ensure_ascii=False,indent=2))
    finally:
        os.close(fd); lock.unlink()


if __name__ == '__main__':
    asyncio.run(main())
