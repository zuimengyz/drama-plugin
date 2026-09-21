"""Project one parsed narrative setting; keep saved revision rhythm immutable."""
from __future__ import annotations
from typing import Any
from drama_plugin.config.models import DramaPluginConfig
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.context import ContextBuildRequest, ContextChange, CreativeRhythm, DramaContextPatch, DramaRunContext
from drama_plugin.exceptions import ContextBuildError, RhythmAuthorityConflict
from drama_plugin.providers.base import ContextProvider

SEMANTICS = {
    "work_defined": "尚未指定全局速度；从当前获准剧本、人物任务和场景节奏推导，不默认紧凑、加速、战争或悲剧。",
    "slow": "允许从容、持续观察与较长接收过程；停留需服务本作品的体验，不能因旧短剧规模自动压缩。",
    "medium": "自然、紧凑而相对从容；保留必要环境认知、人物观察、关键动作过程与有作用的反应停顿，不以重复搬放、空等或完整工艺演示填时长。",
    "fast": "更早进入矛盾或有效行动，及时切向结果、反应与下一步变化；省略无新增信息的重复准备和收拾；自然地让对白、操作和观察并行，让关键细节兼顾人物、事实和关系变化。",
}
COMMON = "各档均非播放或台词倍速，不统一乘时长系数，不设镜头时长/动作密度/切镜次数硬指标。保留观众导航、关键事实、核心动作与时间因果；普通瑕疵不阻断。节奏不选择媒体模型、分辨率、费用或声音服务。"

def validate_rhythm_assertions(options: dict[str, Any], authority: CreativeRhythm) -> None:
    """Task spellings assert one decision; none can create a second authority."""
    assertions = [(f"options.{key}", options[key]) for key in ("rhythm_speed", "rhythmSpeed") if key in options]
    for container in ("creativeRhythm", "creative_rhythm"):
        if container not in options:
            continue
        payload = options[container]
        if not isinstance(payload, dict):
            raise RhythmAuthorityConflict(f"RHYTHM_AUTHORITY_CONFLICT: options.{container} must assert a rhythm value")
        keys = [key for key in ("rhythm_speed", "rhythmSpeed") if key in payload]
        if not keys:
            raise RhythmAuthorityConflict(f"RHYTHM_AUTHORITY_CONFLICT: options.{container} is missing rhythm_speed")
        assertions.extend((f"options.{container}.{key}", payload[key]) for key in keys)
    for path, value in assertions:
        if not isinstance(value, str) or value.strip() != authority.rhythm_speed:
            raise RhythmAuthorityConflict(f"RHYTHM_AUTHORITY_CONFLICT: {path} disagrees with {authority.source}")

class RhythmContextProvider:
    def __init__(self, provider: ContextProvider, config: DramaPluginConfig) -> None:
        self.provider = provider
        self.rhythm = CreativeRhythm(rhythm_speed=config.rhythm_speed, source=config.rhythm_source,
                                     semantics=SEMANTICS[config.rhythm_speed] + COMMON)

    async def build_context(self, request: ContextBuildRequest) -> DramaRunContext:
        return await self._build_context(request)

    async def _build_context(self, request: ContextBuildRequest, preserved: CreativeRhythm | None = None) -> DramaRunContext:
        # New contexts assert parsed runtime configuration. Resume/refresh assert
        # their saved authority, whose immutability is part of this contract.
        revision_id = request.options.get("creativeRevisionId")
        if preserved is not None or not revision_id:
            validate_rhythm_assertions(request.options, preserved or self.rhythm)
        # An explicit new-Work context precedes the first reviewed domain write.
        # Never probe an existing object or silently treat a missing ID as new.
        if request.options.get("newWork") is True:
            if request.scope != "WORK" or request.purpose != "WORK_CREATION" or request.options.get("creativeRevisionId"):
                raise ContextBuildError("newWork requires WORK/WORK_CREATION without a saved revision")
            context = DramaRunContext(
                context_id=f"drama:creation:{request.resource_id}", version=1,
                scope=request.scope, purpose=str(request.purpose),
                research_context=dict(request.options.get("researchContext", {})),
                temporary_state={"newWork": True},
            )
        else:
            context = await self.provider.build_context(request)
        if revision_id:
            revisions = context.work.content.get("creativeRevisions", {}) if context.work else {}
            revision = revisions.get(revision_id)
            if not revision or not revision.get("rhythm"):
                raise ContextBuildError("Saved creativeRevisionId and rhythm required for resume")
            context.creative_rhythm = CreativeRhythm.model_validate(revision["rhythm"])
        else:
            context.creative_rhythm = self.rhythm.model_copy(deep=True)
        if preserved is not None:
            context.creative_rhythm = preserved.model_copy(deep=True)
        validate_rhythm_assertions(request.options, context.creative_rhythm)
        return context

    async def refresh_context(self, request: ContextBuildRequest, current: DramaRunContext) -> DramaContextPatch:
        rebuilt = await self._build_context(request, current.creative_rhythm)
        before = dump_contract(current, exclude={"version", "built_at"})
        after = dump_contract(rebuilt, exclude={"version", "built_at"})
        changes = [ContextChange(operation="replace" if k in before else "add", path="/"+k, value=v)
                   for k,v in after.items() if before.get(k) != v]
        changes += [ContextChange(operation="remove",path="/"+k) for k in before if k not in after]
        return DramaContextPatch(context_id=current.context_id,base_version=current.version,
                                 new_version=current.version+1,changes=changes)
