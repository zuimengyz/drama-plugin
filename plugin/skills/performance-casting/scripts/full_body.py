"""Explicit single-candidate handoff; does not submit to a provider."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src'))
from drama_plugin.contracts.performance_casting import RoleArchetypeProfile
from drama_plugin.contracts.casting_discriminants import VisualCastingPlan
from drama_plugin.contracts.visual_route import RouteCastingContext
from drama_plugin.full_body_casting import FullBodyCastingSpec, executable_full_body, reserve_full_body
from drama_plugin.hosts.mcp_media import McpMediaSession


async def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['brief', 'reserve'])
    for name in ('profile', 'visual-plan', 'route-context', 'spec', 'mcp-config', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--work-id', required=True)
    p.add_argument('--authorization-id', required=True)
    p.add_argument('--request', type=Path)
    p.add_argument('--ledger-root', type=Path)
    a = p.parse_args()
    profile = RoleArchetypeProfile.model_validate_json(a.profile.read_text())
    plan = VisualCastingPlan.model_validate_json(a.visual_plan.read_text())
    context = RouteCastingContext.model_validate_json(a.route_context.read_text())
    spec = FullBodyCastingSpec.model_validate_json(a.spec.read_text())
    async with McpMediaSession(a.mcp_config) as s:
        required = {'work.get_work', 'work.save_work', 'media.import_media', 'media.get_media',
                    'media.list_media', 'media.resolve_media'}
        if not required <= s.names:
            raise ValueError('DURABLE_CASTING_TOOLS_MISSING')
        if a.mode == 'brief':
            work = await s.memory.get_work(a.work_id)
            result = executable_full_body(work, profile, plan, context, spec, a.authorization_id)
        else:
            if not a.request or not a.ledger_root:
                p.error('reserve requires --request and --ledger-root')
            result = await reserve_full_body(s.memory, a.work_id, profile, plan, context, spec,
                a.authorization_id, json.loads(a.request.read_text()), a.ledger_root)
        result['toolCalls'] = s.calls
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    asyncio.run(main())
