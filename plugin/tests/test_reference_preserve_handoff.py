"""Existing fictional contracts only; no author creativity or image-effect claims."""
from copy import deepcopy
import json
import socket
import subprocess

import pytest

from drama_plugin.professional_design.reference_design import inherit_design, verify_design_delivery
from drama_plugin.providers.ark_image import image_payload
from drama_plugin.visual.frame_request import compile_frame
from drama_plugin.visual.prompt_ir import compile_ir
from test_target_reference_production import reference_frame
from test_visual_prompt_ir import fact, visual_ir
from test_work_aesthetic_delivery import PALETTES, PROOF_LOOKS, semantic_art


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("No network, subprocess or media generation is authorized")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(subprocess, "Popen", deny)
    monkeypatch.setenv("DRAMA_PLUGIN_ROUTE_IMAGE_MODEL", "Doubao-Seedream-5.0-pro")


@pytest.fixture
def selected_asset():
    # Same fictional Workshop and material relationship as the existing delivery
    # suite and audit counterexample; no current film design is authored here.
    return {
        "assetType": "LOCATION", "name": "Workshop", "subjectId": None,
        "designRef": {"key": "fictional-probe:look", "kind": "DIRECTION", "fingerprint": "a" * 64},
        "design": {"architecture": "Two bays with a fixed left doorway",
                   "material": PROOF_LOOKS["restrained"]["LOCATION"]},
    }


def artwork(item, preserve):
    frame = reference_frame(item)
    ir = deepcopy(frame.prompt_ir)
    ir["preserve"] = deepcopy(preserve)
    return frame.model_copy(update={"prompt_ir": ir})


def relationship(item):
    # A current material/light relationship already present in the existing
    # semantic author fixture, now testing its other supported contract location.
    value = semantic_art(item, item["design"]["material"])["prompt_ir"]["lighting"]["realism"]
    return fact(value["text"])


def final_wire(frame, item):
    following = inherit_design(frame, item)
    compiled = compile_frame(following)
    verify_design_delivery(compiled, item)
    body = json.loads(json.dumps(compiled["request"]["body"]))
    return following, compiled, body


def test_artwork_only_current_relationship_reaches_final_body(selected_asset):
    authored = relationship(selected_asset)
    original = artwork(selected_asset, [authored])
    following, compiled, body = final_wire(original, selected_asset)
    assert authored in following.prompt_ir["preserve"]
    assert authored["text"] in body["prompt"]
    receipt = [r for r in compiled["prompt_ir_compilation"]["retained"]
               if r["path"].startswith("preserve[") and r["source"] == authored["source"]]
    assert len(receipt) == 1 and receipt[0]["text"] == authored["text"]
    assert original.prompt_ir["preserve"] == [authored]


def test_other_existing_leaf_can_also_deliver_the_relationship(selected_asset):
    authored = relationship(selected_asset)
    frame = artwork(selected_asset, [authored])
    ir = deepcopy(frame.prompt_ir)
    ir["lighting"]["realism"] = deepcopy(authored)
    frame = frame.model_copy(update={"prompt_ir": ir})
    following, compiled, body = final_wire(frame, selected_asset)
    assert following.prompt_ir["lighting"]["realism"] == authored
    assert authored["text"] in body["prompt"]
    assert any(r["path"] == "lighting.realism" and r["text"] == authored["text"]
               for r in compiled["prompt_ir_compilation"]["retained"])


def test_old_asset_facts_are_rebuilt_exact_duplicates_removed_and_replay_idempotent(selected_asset):
    authored = relationship(selected_asset)
    old = fact(PROOF_LOOKS["celebratory"]["LOCATION"])
    old["source"] = "asset-design/" + "b" * 64 + "/material"
    duplicate_selected = fact(selected_asset["design"]["material"])
    frame = artwork(selected_asset, [old, duplicate_selected, authored, deepcopy(authored)])
    following, first, body = final_wire(frame, selected_asset)
    preserve = following.prompt_ir["preserve"]
    assert old not in preserve and old["text"] not in body["prompt"]
    assert duplicate_selected not in preserve
    selected = [f for f in preserve if f["source"].startswith("asset-design/")]
    assert selected == [dict(text=selected_asset["design"]["material"], priority="CRITICAL",
                             scope="CURRENT", source="asset-design/" + "a" * 64 + "/material")]
    assert preserve.count(authored) == 1
    assert body["prompt"].count(selected_asset["design"]["material"]) == 1
    again = inherit_design(following, selected_asset)
    assert again.model_dump(mode="json") == following.model_dump(mode="json")
    assert compile_frame(again)["request"] == first["request"]


@pytest.mark.parametrize("priority,scope", [
    ("IMPORTANT", "CURRENT"), ("SECONDARY", "CURRENT"),
    ("CRITICAL", "FUTURE"), ("CRITICAL", "INTERNAL"),
    ("CRITICAL", "CAPABILITY"), ("CRITICAL", "CLIP"),
])
def test_only_existing_necessary_current_facts_are_carried(selected_asset, priority, scope):
    optional_or_noncurrent = fact(PALETTES["celebratory"], priority, scope)
    following, _, body = final_wire(artwork(selected_asset, [optional_or_noncurrent]), selected_asset)
    assert optional_or_noncurrent not in following.prompt_ir["preserve"]
    assert optional_or_noncurrent["text"] not in body["prompt"]
    assert selected_asset["design"]["material"] in body["prompt"]


def test_invalid_source_still_fails_the_existing_fact_contract(selected_asset):
    authored = relationship(selected_asset)
    authored["source"] = " "
    with pytest.raises(ValueError, match="VISUAL_PROMPT_FACT_REQUIRES_SINGLE_SCOPED_DESCRIPTION"):
        inherit_design(artwork(selected_asset, [authored]), selected_asset)


def test_uncertain_author_relationships_keep_sources_for_professional_review(selected_asset):
    # These existing alternative fixture palettes are not semantically reconciled.
    # The owner still inherits its selected material; distinct author statements
    # retain their locators instead of this helper inventing an artistic verdict.
    authored = [fact(PALETTES["restrained"]), fact(PALETTES["celebratory"])]
    following, _, body = final_wire(artwork(selected_asset, authored), selected_asset)
    assert all(f in following.prompt_ir["preserve"] and f["text"] in body["prompt"] for f in authored)
    assert selected_asset["design"]["material"] in body["prompt"]


def edit_projection(frame, item):
    ir = deepcopy(frame.prompt_ir)
    provider = ir["task"]["provider_family"]
    existing_edit = visual_ir("REFERENCE_EDIT", provider)
    ir["task"].update(task_type="REFERENCE_EDIT", input_mode="reference")
    ir["edit_delta"] = existing_edit["edit_delta"]
    following = inherit_design(frame.model_copy(update={"prompt_ir": ir}), item)
    compilation = compile_ir(following.prompt_ir, provider_family=provider)
    body = json.loads(json.dumps(image_payload(provider, compilation["prompt"], (2048, 2048), 1)))
    verify_design_delivery({"prompt_ir_compilation": compilation, "request": {"body": body}}, item)
    return following, compilation, body


def test_reference_edit_keeps_authored_relation_outside_the_correction(selected_asset):
    authored = relationship(selected_asset)
    following, compilation, body = edit_projection(artwork(selected_asset, [authored]), selected_asset)
    assert authored in following.prompt_ir["preserve"]
    assert authored["text"] in body["prompt"]
    assert "Keep the supplied image unchanged except for the corrections above." in body["prompt"]
    assert selected_asset["design"]["material"] in body["prompt"]
    assert "MUST CHANGE" in body["prompt"] and compilation["ir"]["edit_delta"]


def test_reference_edit_fallback_still_preserves_outside_regions(selected_asset):
    item = deepcopy(selected_asset)
    item["design"].pop("material")
    old = fact(PROOF_LOOKS["celebratory"]["LOCATION"])
    old["source"] = "asset-design/" + "b" * 64 + "/material"
    following, _, body = edit_projection(artwork(item, [old]), item)
    assert old["text"] not in body["prompt"]
    assert following.prompt_ir["preserve"] == [dict(
        text="Preserve the supplied image outside the explicit edit regions.",
        priority="CRITICAL", scope="CURRENT", source="reference-proof-preservation")]
    assert "Preserve the supplied image outside the explicit edit regions." in body["prompt"]

