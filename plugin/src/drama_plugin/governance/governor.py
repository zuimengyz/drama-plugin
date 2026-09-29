"""The sole stopping-authority governor. No Canon, Prompt or Provider operations."""
from __future__ import annotations

from drama_plugin.governance.contracts import (
    GateCategory as C, GateCode, GateDecision, GateEffect as E, GateFinding, RULES,
)
from drama_plugin.governance.store import GateFindingStore
from drama_plugin.runtime.contracts import ArtifactReference, RunMode, RuntimeScope, UserDecisionRequest

QUESTIONS = {
    GateCode.ART_APPROVAL_REQUIRED: "是否批准该版本的艺术方案？",
    GateCode.COST_APPROVAL_REQUIRED: "是否批准新增范围的费用？",
    GateCode.MAJOR_ADAPTATION_REQUIRED: "是否批准该重大改编？",
    GateCode.ADOPTION_REQUIRED: "是否正式采纳该版本？",
    GateCode.FINAL_ACCEPTANCE_REQUIRED: "是否验收最终交付？",
}
REASONS = {
    GateCode.PACKAGE_SCOPE_MISMATCH: "对象或 Shot scope 不一致，继续可能生产错误对象。",
    GateCode.CANON_AUTHORITY_MISMATCH: "来源 Authority 不合法，继续可能使用越权的正式创作。",
    GateCode.BUDGET_EXCEEDED: "执行超出明确预算，可能造成未授权收费。",
    GateCode.COST_UNAUTHORIZED: "收费缺少必要授权，不能产生该副作用。",
    GateCode.SUBMISSION_UNCERTAIN: "Provider 接收状态不明，重发可能重复收费；先对账。",
    GateCode.OPERATION_IDENTITY_MISMATCH: "操作或结果身份无法对账，可能重复收费或错绑任务。",
    GateCode.REQUEST_INPUT_MISSING: "必需请求输入缺失，当前无法表达合法执行请求。",
    GateCode.REQUEST_UNSUPPORTED: "服务明确不支持必需请求能力，需返回支持的路线。",
    GateCode.PROVIDER_HARD_LIMIT: "请求超过不可规避的服务硬限制。",
    GateCode.PACKAGE_STALE: "ProductionPackage 已过期；内部重新组装，不需要用户维护。",
    GateCode.OPTIONAL_SOURCE_MISSING: "可选质量来源缺失，可能降低表现质量；试拍记录后继续。",
    GateCode.QUALITY_COVERAGE_RISK: "质量覆盖存在风险；试拍继续，正式交付义务可要求评审。",
    GateCode.CONTINUITY_RISK: "连续性存在质量风险，不自动取得收费硬阻断权。",
    GateCode.CAPABILITY_NOT_IMPLEMENTED: "能力尚未实现；需要报告或路由能力缺口，批准不能使它存在。",
    GateCode.LEGACY_ENTRY_REJECTED: "该入口只供旧任务兼容或恢复，不进入新生产主链。",
}


class GateGovernor:
    role = "POLICY_VALIDATION_GOVERNANCE"
    hard_stop_risk_families = 4

    def __init__(self, store: GateFindingStore):
        self.store = store

    def explain(self, decision: GateDecision) -> tuple[str, ...]:
        explanations = []
        for ref in decision.finding_refs:
            finding = self.store.finding(ref)
            reason = REASONS.get(finding.code)
            if reason is None:
                reason = QUESTIONS.get(finding.code, "这是运行时内部技术维护，不要求用户批准技术材料。")
            family = f" / {finding.risk_family.value}" if finding.risk_family else ""
            explanations.append(f"{reason} {finding.category.value}{family}；{decision.effect.value}；owner={finding.owner}。")
        return tuple(explanations)

    def govern(self, findings: tuple[GateFinding, ...], *, scope: RuntimeScope,
               mode: RunMode, package_ref: ArtifactReference | None) -> GateDecision:
        checked = [GateFinding.model_validate(f.model_dump()) for f in findings]
        for finding in tuple(checked):
            if finding.scope != scope:
                checked.append(GateFinding.classified(GateCode.PACKAGE_SCOPE_MISMATCH,
                    owner="gate-governor", scope=scope, evidence_ref=self.store.put_finding(finding)))
        # Deduplicate before the bounded decision record, without dropping distinct evidence.
        refs = tuple(sorted({self.store.put_finding(f) for f in checked},
                            key=lambda ref: ref.artifact_ref))
        hard = [f for f in checked if f.category == C.HARD_STOP]
        user = [f for f in checked if f.category == C.USER_DECISION]
        # T1 supports one genuine decision per step. Never treat approval of one
        # category as approval of an unrelated fee/adoption/adaptation request.
        multiple_decisions = len({f.code for f in user}) > 1
        if multiple_decisions and not hard:
            checked.append(GateFinding.classified(GateCode.CAPABILITY_NOT_IMPLEMENTED,
                owner="multi-decision-coordinator", scope=scope,
                evidence_ref=self.store.put_finding(user[0]), required=True))
            refs = tuple(sorted({self.store.put_finding(f) for f in checked}, key=lambda ref: ref.artifact_ref))
        effect, request = E.CONTINUE, None
        if hard:
            effect = E.BLOCK
        elif any(f.category == C.LEGACY_GUARD for f in checked):
            effect = E.LEGACY_REJECT
        elif multiple_decisions:
            effect = E.CAPABILITY_ABSENT
        elif user:
            effect = E.WAIT_USER
            code = sorted(user, key=lambda f: f.code.value)[0].code
            category = RULES[code][2]
            assert category is not None
            request = UserDecisionRequest(category=category, question=QUESTIONS[code])
        elif any(f.category == C.CAPABILITY_ABSENT and f.required for f in checked):
            effect = E.CAPABILITY_ABSENT
        elif any(f.category == C.AUTO_MAINTENANCE for f in checked):
            effect = E.AUTO_MAINTAIN
        elif mode == RunMode.PRODUCTION and any(f.category == C.WARNING and f.required for f in checked):
            effect = E.REVIEW_REQUIRED
        return GateDecision(scope=scope, mode=mode, effect=effect, finding_refs=refs,
            risk_families=tuple(sorted({f.risk_family for f in hard if f.risk_family is not None})),
            package_ref=package_ref, user_decision=request)
