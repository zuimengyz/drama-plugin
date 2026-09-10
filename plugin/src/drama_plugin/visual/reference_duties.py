"""Reference duty fulfillment, independent of provider dialect and file transport."""
from __future__ import annotations
from typing import Any, Literal
from pydantic import Field
from drama_plugin.contracts.cinematic import ReferenceRole, CinematicShotSpec
from drama_plugin.visual.frame_request import Record, Text, Hash


class ReferenceDuty(Record):
    role: ReferenceRole
    subject: Text
    purpose: Text
    status: Literal['FULFILLED', 'EQUIVALENT'] = 'FULFILLED'
    media_id: Text | None = None
    source_ref: Text | None = None
    content_hash: Hash | None = None
    mime_type: Text | None = None
    provider_input_type: Literal['IMAGE', 'VIDEO', 'AUDIO', 'TEXT']
    provider_slot: Text
    target_shot: Text
    fulfills: tuple[Text, ...] = Field(min_length=1)
    evidence: Text
    # Only non-identity spatial/effect duties may be explicitly realized by the
    # exact frozen direction text. A missing performance reference stays missing.
    equivalent_text: Text | None = None


def validate_duties(spec: CinematicShotSpec, inputs: tuple[Any, ...],
                    duties: tuple[ReferenceDuty, ...]) -> list[str]:
    requirements = {(r.role, r.subject): r for r in spec.reference_requirements}
    if len(requirements) != len(spec.reference_requirements):
        raise ValueError('DUPLICATE_REFERENCE_REQUIREMENT')
    bound = set()
    for duty in duties:
        key = (duty.role, duty.subject)
        req = requirements.get(key)
        if req is None or key in bound or duty.purpose != req.purpose or duty.target_shot != spec.shot_id:
            raise ValueError('REFERENCE_WRONG_DUTY_SCOPE_OR_PURPOSE')
        if duty.status == 'EQUIVALENT':
            texts = [spec.opening_state, spec.ending_state] + ['；'.join((x.source,x.effect,x.affected,x.response,x.occlusion_or_depth)) for x in spec.environment_interaction]
            if (duty.role not in {'LOCATION', 'COMPOSITION', 'VFX'} or duty.provider_input_type != 'TEXT'
                    or duty.provider_slot != 'prompt' or duty.equivalent_text not in texts or duty.media_id):
                raise ValueError('UNSUPPORTED_REFERENCE_EQUIVALENT')
        else:
            inp = next((i for i in inputs if i.media_id == duty.media_id), None)
            if inp is None or any(getattr(inp, k) != getattr(duty, k) for k in ('source_ref','content_hash','mime_type')):
                raise ValueError('REFERENCE_MEDIA_IDENTITY_MISMATCH')
            if not duty.source_ref or not duty.content_hash or not duty.mime_type:
                raise ValueError('REFERENCE_FORMAL_IDENTITY_REQUIRED')
            if duty.provider_input_type != 'IMAGE' or not duty.mime_type.startswith('image/'):
                raise ValueError('PROJECT_IMAGE_INPUT_CONTRACT')
            if duty.role in {'PERFORMANCE', 'CAMERA_MOTION'}:
                raise ValueError('STATIC_IMAGE_CANNOT_FULFILL_MOTION_REFERENCE')
            if req.establishes_opening_state and inp.role != 'FIRST_FRAME':
                raise ValueError('CHARACTER_REFERENCE_IS_NOT_FIRST_FRAME')
        bound.add(key)
    missing = [r.role + ':' + r.subject for key, r in requirements.items() if r.necessity == 'REQUIRED' and key not in bound]
    if missing:
        raise ValueError('REQUIRED_REFERENCE_UNFULFILLED:' + ','.join(missing))
    return [r.role + ':' + r.subject for key, r in requirements.items() if key not in bound]


def validate_media_snapshot(inp: Any, snapshot: dict[str, Any], *, work_id: str) -> None:
    if (snapshot.get('id') != inp.media_id or snapshot.get('work_id') != work_id
            or any(snapshot.get(k) != getattr(inp, k) for k in ('source_ref','content_hash','mime_type'))
            or snapshot.get('media_type') != 'IMAGE'):
        raise ValueError('FORMAL_REFERENCE_MEDIA_CHANGED')


def validate_endpoint(inp: Any, spec: CinematicShotSpec) -> None:
    expected = {'FIRST_FRAME': spec.opening_state, 'LAST_FRAME': spec.ending_state}.get(inp.role)
    if expected and (inp.endpoint_state != expected or not inp.endpoint_evidence):
        raise ValueError('ENDPOINT_STATE_REQUIRES_OBSERVED_MATCH_OR_REPLAN')
