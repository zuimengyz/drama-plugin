"""Image request preflight for Host-owned visual execution; no provider calls.

These are run-context records, not Drama domain entities. Provider slot metadata
must come from the Host's inspected official template, never from reference count.
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from drama_plugin.contracts.base import sha256_canonical

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Reference(Record):
    entity_key: Text
    kind: Literal["CHARACTER", "PROP", "SCENE", "COSTUME"]
    asset_id: Text
    media_id: Text
    version: Text
    content_hash: Hash
    local_path: Text
    upload_name: Text
    uploaded_hash: Hash
    upload_receipt: Text
    facts: Text
    state: Text
    review: Literal["PASS", "ACCEPTABLE_INTERPRETATION"]


class Actor(Record):
    entity_key: Text
    label: Text
    identity: Text
    costume: Text
    position: Text
    pose: Text
    action: Text
    gaze: Text
    visibility: Literal["FACE", "PARTIAL", "POV"] = "FACE"


class Prop(Record):
    entity_key: Text
    state: Text
    geometry: Text
    placement: Text
    forbidden: tuple[Text, ...] = Field(min_length=1)
    # Explicit, Shot-owned exception when a reference depicts the previous state.
    reference_delta: Text | None = None


class FrameSpec(Record):
    shot_id: Text
    shot_fingerprint: Hash
    entry_state: Text
    composition: Text
    environment: Text
    actors: tuple[Actor, ...] = ()
    props: tuple[Prop, ...] = ()
    required: tuple[Text, ...] = Field(min_length=1)
    forbidden: tuple[Text, ...] = Field(min_length=1)
    references: tuple[Reference, ...] = Field(max_length=3)
    # A frozen asset/version lock resolved before this campaign, not 'latest'.
    reference_lock: dict[str, Hash]
    # Must explicitly account for secondary omitted references within the cap.
    omitted: dict[str, Text] = Field(default_factory=dict)
    shot_type: Literal["SINGLE_STATIC", "TWO_PERSON", "PERSON_PROP", "COMPLEX_POSE", "ESTABLISHING"]
    target_size: tuple[int, int]
    crop_review: Text | None = None
    seed: int = Field(ge=0)


class Template(Record):
    name: Text
    model: Text
    evidence: Text
    graph_hash: Hash
    graph_path: Text
    # Ordered in actual model image_1/image_2/... order, not node number order.
    image_slots: tuple[Text, ...]
    prompt_node: Text
    prompt_key: Text = "prompt"
    seed_key: Text = "seed"
    output_size: tuple[int, int]
    settings: dict[str, Any] = Field(default_factory=dict)
    # Capability evidence is distinct from an artistic PASS on this task.
    supported_types: tuple[Text, ...] = Field(min_length=1)


def _unique(values: list[str], error: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(error)


def _verify_graph(spec: FrameSpec, template: Template) -> None:
    graph = json.loads(Path(template.graph_path).read_text())
    if sha256_canonical(graph) != template.graph_hash:
        raise ValueError("TEMPLATE_GRAPH_CHANGED")
    nodes = {str(n['id']): n for n in graph['nodes']}
    links = {link[0]: link for link in graph['links']}
    model = nodes[template.prompt_node]
    widgets = model.get('widgets_values_named', {})
    if template.prompt_key not in widgets or template.seed_key not in widgets:
        raise ValueError("TEMPLATE_PROMPT_OR_SEED_SLOT_NOT_VERIFIED")
    images = []
    for port in model.get('inputs', []):
        match = re.search(r'(?:^|\.)image_(\d+)$', port['name'])
        if match and port.get('link') is not None:
            images.append((int(match[1]), str(links[port['link']][1])))
    ordered = tuple(slot for _, slot in sorted(images))
    if ordered != template.image_slots or any(nodes[s]['type'] != 'LoadImage' for s in ordered):
        raise ValueError("TEMPLATE_IMAGE_WIRING_MISMATCH")
    # Verify directly linked dimensions (including the audited Flux GetImageSize
    # trap). Unsupported derived graphs stop instead of guessing a safe crop.
    dimensions = []
    for key, axis in [('model.width', 0), ('model.height', 1)]:
        dimension_port: dict[str, Any] = next((p for p in model.get('inputs', []) if p['name'] == key), {})
        if dimension_port.get('link') is None:
            value = widgets.get(key)
        else:
            size_node = nodes[str(links[dimension_port['link']][1])]
            if size_node['type'] != 'GetImageSize':
                raise ValueError("UNSUPPORTED_TEMPLATE_DIMENSION_SOURCE")
            source = next(p for p in size_node['inputs'] if p['name'] == 'image')
            slot = str(links[source['link']][1])
            ref = spec.references[template.image_slots.index(slot)]
            with Path(ref.local_path).open('rb') as stream:
                header = stream.read(24)
            if not header.startswith(b'\x89PNG\r\n\x1a\n') or len(header) != 24:
                raise ValueError("LINKED_DIMENSION_PROBE_REQUIRES_PNG")
            value = struct.unpack('>II', header[16:24])[axis]
        if not isinstance(value, int) or value <= 0:
            raise ValueError("UNVERIFIED_TEMPLATE_OUTPUT_SIZE")
        dimensions.append(value)
    if tuple(dimensions) != template.output_size:
        raise ValueError("TEMPLATE_OUTPUT_SIZE_MISMATCH")


def compile_frame(spec: FrameSpec, template: Template) -> dict[str, Any]:
    # Revalidate even model_copy/update callers; Pydantic does not validate updates.
    spec = FrameSpec.model_validate(spec.model_dump())
    template = Template.model_validate(template.model_dump())
    if len(template.image_slots) != len(spec.references):
        raise ValueError("REFERENCE_SLOT_COUNT_MISMATCH")
    _unique(list(template.image_slots), "DUPLICATE_PROVIDER_SLOT")
    if template.prompt_node in template.image_slots:
        raise ValueError("PROMPT_IMAGE_SLOT_COLLISION")
    if template.prompt_key in template.settings or template.seed_key in template.settings:
        raise ValueError("TEMPLATE_CANNOT_OVERRIDE_SHOT_PROMPT_OR_SEED")
    if any(key not in {'model.quality'} for key in template.settings):
        raise ValueError("UNVERIFIED_TEMPLATE_SETTING")
    if spec.shot_type not in template.supported_types:
        raise ValueError("MODEL_INTENT_NOT_VERIFIED")
    if min(*template.output_size, *spec.target_size) <= 0:
        raise ValueError("INVALID_FRAME_SIZE")
    tw, th = template.output_size
    sw, sh = spec.target_size
    if tw * sh != th * sw and not spec.crop_review:
        raise ValueError("OUTPUT_ASPECT_REQUIRES_CROP_REVIEW_OR_OTHER_TEMPLATE")
    _unique([a.entity_key for a in spec.actors], "DUPLICATE_ACTOR")
    _unique([a.label.casefold() for a in spec.actors], "DISTINCT_ACTOR_LABELS_REQUIRED")
    _unique([r.entity_key for r in spec.references], "DUPLICATE_REFERENCE_ENTITY")
    _unique([r.media_id for r in spec.references], "REFERENCE_MEDIA_REUSED_FOR_DISTINCT_ENTITIES")
    _unique([r.upload_name for r in spec.references], "UPLOAD_REUSED_FOR_DISTINCT_ENTITIES")
    refs = {r.entity_key: r for r in spec.references}
    if set(spec.omitted) & set(refs):
        raise ValueError("REFERENCE_BOTH_SELECTED_AND_OMITTED")
    for r in spec.references:
        lock_key = f"{r.asset_id}/{r.media_id}/{r.version}"
        if spec.reference_lock.get(lock_key) != r.content_hash:
            raise ValueError("REFERENCE_VERSION_NOT_LOCKED")
        if hashlib.sha256(Path(r.local_path).read_bytes()).hexdigest() != r.content_hash:
            raise ValueError("REFERENCE_LOCAL_HASH_MISMATCH")
        if r.uploaded_hash != r.content_hash:
            raise ValueError("REFERENCE_UPLOAD_HASH_MISMATCH")
        receipt = json.loads(Path(r.upload_receipt).read_text())
        if receipt.get('name') != r.upload_name or receipt.get('content_hash') != r.content_hash:
            raise ValueError("REFERENCE_UPLOAD_RECEIPT_MISMATCH")
    for a in spec.actors:
        if a.entity_key not in refs or refs[a.entity_key].kind != "CHARACTER":
            raise ValueError("MISSING_STABLE_REFERENCE:" + a.entity_key)
    _verify_graph(spec, template)
    risks: set[str] = {spec.shot_type}
    if len(spec.actors) > 1:
        risks.add("MULTI_IDENTITY")
    for p in spec.props:
        if p.entity_key in refs and refs[p.entity_key].kind not in {'PROP', 'SCENE'}:
            raise ValueError("FOCAL_PROP_BOUND_TO_WRONG_REFERENCE_KIND")
        if p.entity_key not in refs and p.entity_key not in spec.omitted:
            raise ValueError("FOCAL_PROP_REFERENCE_UNACCOUNTED_FOR")
        if p.entity_key in refs and refs[p.entity_key].state != p.state:
            if not p.reference_delta:
                raise ValueError("PROP_REFERENCE_STATE_CONFLICT")
            risks.add("STATE_TRANSITION:" + p.entity_key + ":" + p.state)
        elif p.entity_key not in refs:
            risks.add("OMITTED_PROP:" + p.entity_key + ":" + p.state)
    # No future motion or generic posture argument: one observable entry moment.
    parts = ["ONE cinematic frame at the Shot entry moment.",
             "SHOT BLOCKING owns pose, screen position, action and gaze. Reference poses do not transfer.",
             f"ENTRY: {spec.entry_state}", f"COMPOSITION: {spec.composition}"]
    for index, r in enumerate(spec.references, 1):
        parts.append(f"Image {index} binds ONLY {r.entity_key} ({r.kind}); {r.facts}. Reference state: {r.state}.")
    for a in spec.actors:
        parts.append(f"ACTOR {a.label} [{a.entity_key}]: identity={a.identity}; costume={a.costume}; "
                     f"position={a.position}; pose={a.pose}; action NOW={a.action}; gaze={a.gaze}; visibility={a.visibility}.")
    if len(spec.actors) > 1:
        parts.append("Keep each named actor's face, age, hair, beard and costume attached to that actor's blocking. "
                     "No identity swap, duplicate principal or transfer of clothes between actors.")
    for p in spec.props:
        parts.append(f"PROP {p.entity_key}: state NOW={p.state}; geometry={p.geometry}; placement={p.placement}; "
                     f"forbidden={'; '.join(p.forbidden)}.")
        if p.reference_delta:
            parts.append(f"SHOT-OWNED REFERENCE DELTA for {p.entity_key}: {p.reference_delta}")
    parts += [f"ENVIRONMENT: {spec.environment}", "MUST SHOW: " + "; ".join(spec.required),
              "MUST NOT SHOW: " + "; ".join(spec.forbidden)]
    prompt = "\n".join(parts)
    overrides: dict[str, Any] = {slot: {"image": ref.upload_name} for slot, ref in zip(template.image_slots, spec.references)}
    overrides[template.prompt_node] = {**template.settings, template.prompt_key: prompt, template.seed_key: spec.seed}
    request = {"tool": "run_template", "name": template.name, "description": spec.shot_id + "-frame", "input_overrides": overrides}
    material = {"schema": "visual-frame-preflight-v1", "spec": spec.model_dump(mode="json"),
                "template": template.model_dump(mode="json"), "request": request, "risks": sorted(risks)}
    return {**material, "fingerprint": sha256_canonical(material)}


def verify_compiled(compiled: dict[str, Any]) -> None:
    expected = compile_frame(FrameSpec.model_validate(compiled["spec"]), Template.model_validate(compiled["template"]))
    if compiled != expected:
        raise ValueError("STALE_OR_MODIFIED_FRAME_REQUEST")
