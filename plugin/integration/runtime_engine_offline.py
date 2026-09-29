"""完全离线的 T1 主循环 fixture；不连接服务、不生成媒体、不写正式 Work。"""
from __future__ import annotations

import argparse
import asyncio
import json
import socket
from pathlib import Path
from typing import Any
from unittest.mock import patch

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.creation import Work
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.runtime import InMemoryRunStore, RunMode, RuntimeEngine, RuntimeRun, RuntimeState


class RecordingStore(InMemoryRunStore):
    """Fixture-only trace, not persistent runtime history."""
    def __init__(self) -> None:
        super().__init__()
        self.trace: list[str] = []

    def create(self, run: RuntimeRun) -> RuntimeRun:
        result = super().create(run)
        self.trace.append(result.state.value)
        return result

    def save(self, run: RuntimeRun, *, expected_revision: int) -> RuntimeRun:
        result = super().save(run, expected_revision=expected_revision)
        self.trace.append(result.state.value)
        return result


def forbidden(*args: Any, **kwargs: Any) -> Any:
    raise AssertionError("T1 离线验证禁止网络和生成调用")


async def run() -> dict[str, Any]:
    data = MockDramaData.empty()
    data.work = Work(id="t1-offline-work", title="T1 离线 fixture", content={})
    before = data.work.model_dump_json()
    # Explicit default mock config: ambient production credentials are never loaded.
    with patch("drama_plugin.plugin.load_config", return_value=DramaPluginConfig()), \
         patch.object(socket.socket, "connect", forbidden), \
         patch.object(socket.socket, "connect_ex", forbidden):
        async with DramaPlugin.load(Path(__file__).resolve().parents[1], mock_data=data) as plugin:
            calls: list[str] = []
            original = plugin.tools.invoke

            async def invoke(code: str, **arguments: Any) -> Any:
                calls.append(code)
                return await original(code, **arguments)

            with patch.object(plugin.tools, "invoke", invoke), \
                 patch.object(plugin.providers.production, "generate_image", forbidden), \
                 patch.object(plugin.providers.production, "generate_video", forbidden):
                initial_store = RecordingStore()
                plugin.runtime = RuntimeEngine(plugin.runtime.executor, store=initial_store)
                initial = plugin.runtime.create_run(work_id=data.work.id, mode=RunMode.EXPERIMENT,
                    run_id="t1-offline-run")
                planned_action = plugin.runtime.next_action(initial.run_id)
                ready = await plugin.runtime.run(initial.run_id, max_ticks=1)
                before_action = plugin.runtime.next_action(initial.run_id)
                snapshot = plugin.runtime.serialize(initial.run_id)
                restored_store = RecordingStore()
                plugin.runtime = RuntimeEngine(plugin.runtime.executor, store=restored_store)
                restored = plugin.runtime.restore(snapshot)
                same_action = plugin.runtime.next_action(initial.run_id) == before_action
                completed = await plugin.runtime.run(initial.run_id)
                again = await plugin.runtime.run(initial.run_id)
                checks = {
                    "计划状态正确": initial.state == RuntimeState.PLANNED,
                    "Plugin自行计算下一步": planned_action.capability_key == "work.get_work",
                    "检查点恢复一致": ready == restored and same_action,
                    "主循环自行完成": completed.state == RuntimeState.SUCCEEDED,
                    "终态不重复调用": again == completed and calls == ["work.get_work"],
                    "原件没有变化": data.work.model_dump_json() == before,
                    "运行状态只有引用": data.work.title not in plugin.runtime.serialize(initial.run_id),
                }
                assert all(checks.values()), checks
                return {"验证等级": "OFFLINE_T1_FOUNDATION", "检查": checks,
                    "状态轨迹": initial_store.trace + restored_store.trace[1:],
                    "实际调用": calls, "最终运行状态": json.loads(plugin.runtime.serialize(initial.run_id)),
                    "持久化边界": restored_store.durability,
                    "迁移桥": plugin.runtime.executor.lifecycle,
                    "Provider付费调用": 0, "媒体生成": 0, "正式数据写入": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = asyncio.run(run())
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
