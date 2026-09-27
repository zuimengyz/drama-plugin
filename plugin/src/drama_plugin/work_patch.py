"""Narrow production persistence; no new creative or execution authority."""
from typing import Any
from drama_plugin.contracts.creation import Work
from drama_plugin.creative_source import validate_work_content
from drama_plugin.exceptions import RemoteServiceError

def validate_patch(work: Work, expected_version: int, changes: dict[str, Any]) -> None:
    if type(expected_version) is not int or expected_version != work.version:
        raise RemoteServiceError("Work version changed", error_code="CONFLICT")
    if not changes or not set(changes) <= {"productionStage", "continuityPacks"}:
        raise ValueError("Only productionStage/continuityPacks patch is allowed")
    if "continuityPacks" in changes:
        validate_reference_rebinding(work, changes["continuityPacks"])
    if "productionStage" in changes:
        from drama_plugin.visual.production import check_campaign
        stage = changes["productionStage"]
        if not isinstance(stage, dict) or not isinstance(stage.get("attempts"), list):
            raise ValueError("Malformed productionStage")
        previous = work.content.get("productionStage")
        if ((previous is not None and stage.get("stage") != previous.get("stage"))
                or stage.get("production_route") != work.content.get("productionRoute")
                or (previous is None and stage.get("stage", {}).get("id") != work.content.get("productionRoute", {}).get("stage_id"))):
            raise ValueError("Production stage/route binding changed")
        check_campaign(stage)
    validate_work_content({**work.content, **changes}, work.content)


def validate_reference_rebinding(work: Work, packs: dict[str, Any]) -> None:
    from drama_plugin.contracts.video import ContinuityPack
    from drama_plugin.contracts.base import sha256_canonical
    from drama_plugin.visual.production import current_review
    old = work.content.get("continuityPacks", {})
    if not isinstance(packs, dict) or set(packs) != set(old):
        raise ValueError("CANONICAL_PACK_SET_CHANGED")
    stage = work.content.get("productionStage", {})
    for key, raw in packs.items():
        if raw == old[key]:
            continue
        pack = ContinuityPack.model_validate(raw)
        previous = ContinuityPack.model_validate(old[key])
        exclude = {"references", "required_reference_ids"}
        if pack.work_id != work.id or pack.segment_id != key or pack.model_dump(exclude=exclude) != previous.model_dump(exclude=exclude):
            raise ValueError("CANONICAL_CREATIVE_CONTENT_CHANGED")
        if len(pack.references) != len(previous.references):
            raise ValueError("CANONICAL_REFERENCE_DUTIES_CHANGED")
        replacement = {a.media_id: b.media_id for a, b in zip(previous.references, pack.references)}
        if pack.required_reference_ids != tuple(replacement[x] for x in previous.required_reference_ids):
            raise ValueError("CANONICAL_REFERENCE_DUTIES_CHANGED")
        for ref, prior in zip(pack.references, previous.references):
            if (ref.kind, ref.semantics, ref.prompt_binding) != (prior.kind, prior.semantics, prior.prompt_binding):
                raise ValueError("CANONICAL_REFERENCE_DUTIES_CHANGED")
            selected = next((v for v in stage.get("input_selections", {}).values() if v.get("media_id") == ref.media_id), None)
            if not selected or selected.get("content_hash") != ref.content_hash:
                raise ValueError("REFERENCE_NOT_SELECTED_OR_CHANGED")
            attempt = next((v for v in stage.get("attempts", []) if v["attempt_id"] == selected["attempt_id"]), None)
            if not attempt or not attempt.get("review_status", "").startswith("PASS"):
                raise ValueError("REFERENCE_CONTENT_REVIEW_FAILED")
            review_hash = sha256_canonical(current_review(attempt))
            if selected.get("review_hash") != review_hash or ref.review_ref != "production-review:"+attempt["attempt_id"]+"@"+review_hash:
                raise ValueError("REFERENCE_REVIEW_CHANGED")
