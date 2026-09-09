"""Project one parsed narrative setting; keep saved revision rhythm immutable."""
from __future__ import annotations
from drama_plugin.config.models import DramaPluginConfig
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.context import ContextBuildRequest, ContextChange, CreativeRhythm, DramaContextPatch, DramaRunContext
from drama_plugin.exceptions import ContextBuildError
from drama_plugin.providers.base import ContextProvider

SEMANTICS = {
    "medium": "自然、紧凑而相对从容；保留必要环境认知、人物观察、关键动作过程与有作用的反应停顿，不以重复搬放、空等或完整工艺演示填时长。",
    "fast": "更早进入矛盾或有效行动，及时切向结果、反应与下一步变化；省略无新增信息的重复准备和收拾；自然地让对白、操作和观察并行，让关键细节兼顾人物、事实和关系变化。",
}
COMMON = "两档均非播放或台词倍速，不统一乘时长系数，不设镜头时长/动作密度/切镜次数硬指标。保留观众导航、关键事实、核心动作与时间因果；普通瑕疵不阻断。节奏不选择媒体模型、分辨率、费用或声音服务。"

class RhythmContextProvider:
    def __init__(self, provider: ContextProvider, config: DramaPluginConfig) -> None:
        self.provider = provider
        self.rhythm = CreativeRhythm(rhythm_speed=config.rhythm_speed, source=config.rhythm_source,
                                     semantics=SEMANTICS[config.rhythm_speed] + COMMON)

    async def build_context(self, request: ContextBuildRequest) -> DramaRunContext:
        context = await self.provider.build_context(request)
        revision_id = request.options.get("creativeRevisionId")
        if revision_id:
            revisions = context.work.content.get("creativeRevisions", {}) if context.work else {}
            revision = revisions.get(revision_id)
            if not revision or not revision.get("rhythm"):
                raise ContextBuildError("Saved creativeRevisionId and rhythm required for resume")
            context.creative_rhythm = CreativeRhythm.model_validate(revision["rhythm"])
        else:
            context.creative_rhythm = self.rhythm.model_copy(deep=True)
        return context

    async def refresh_context(self, request: ContextBuildRequest, current: DramaRunContext) -> DramaContextPatch:
        rebuilt = await self.build_context(request)
        # Refresh follows an existing revision. New configuration requires a new build.
        if current.creative_rhythm is not None:
            rebuilt.creative_rhythm = current.creative_rhythm.model_copy(deep=True)
        before = dump_contract(current, exclude={"version", "built_at"})
        after = dump_contract(rebuilt, exclude={"version", "built_at"})
        changes = [ContextChange(operation="replace" if k in before else "add", path="/"+k, value=v)
                   for k,v in after.items() if before.get(k) != v]
        changes += [ContextChange(operation="remove",path="/"+k) for k in before if k not in after]
        return DramaContextPatch(context_id=current.context_id,base_version=current.version,
                                 new_version=current.version+1,changes=changes)
