#!/usr/bin/env python3
"""Plan and reserve a new story through its existing formal Work and visual stage."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src'))
from drama_plugin.hosts.mcp_media import McpMediaSession
from drama_plugin.hosts.route_production import operate, save_route
from drama_plugin.hosts.comfy_video import verify_execution
from drama_plugin.visual import production


async def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['save-route','check-input','init-stage','add-frame','reserve',
                    'result','billing','usage','review','inspect','persist','replan','retry-not-created'])
    p.add_argument('--mcp-config', type=Path, required=True)
    p.add_argument('--work-id', required=True)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--snapshot-dir', type=Path, required=True)
    a = p.parse_args()
    a.snapshot_dir.mkdir(parents=True, exist_ok=True)
    lock = a.snapshot_dir / (a.work_id + '.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        production.video_verifier = verify_execution
        async with McpMediaSession(a.mcp_config) as session:
            payload = json.loads(a.input.read_text())
            result = (await save_route(session.memory, a.work_id, payload) if a.command == 'save-route'
                      else await operate(session.memory, a.work_id, a.command, payload))
            if 'state' in result:
                (a.snapshot_dir / 'state.json').write_text(json.dumps(result['state'], ensure_ascii=False, indent=2))
            print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        os.close(fd)
        lock.unlink()


if __name__ == '__main__':
    asyncio.run(main())
