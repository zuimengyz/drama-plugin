"""Source-bound witnesses on existing DPD; never another intent authority."""
from __future__ import annotations

from typing import Annotated, Literal
from typing import Any
from pydantic import Field, StringConstraints, model_validator, model_serializer, SerializerFunctionWrapHandler
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.cinematic import ObservableAction

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class BeatPlayability(ContractModel):
    action_carrier_refs: tuple[Text, ...] = ()
    reaction_carrier_ref: Text | None = None
    source_scene_hash: Hash
    source_excerpt: Text
    playable_actions: tuple[ObservableAction, ...] = Field(min_length=1)
    performance_state: Text
    state_scope: Literal["CURRENT_BEAT"] = "CURRENT_BEAT"
    reaction: ObservableAction
    review_evidence: Text

    @model_serializer(mode='wrap')
    def legacy_wire(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        if not self.action_carrier_refs:
            data.pop('actionCarrierRefs', None)
        if self.reaction_carrier_ref is None:
            data.pop('reactionCarrierRef', None)
        return data


class LinePlayability(ContractModel):
    source_text_hash: Hash
    literal_meaning: Text
    speakability_review: Text
    fragmentation: Literal["CONTINUOUS", "INTENTIONAL", "INTENTIONALLY_UNINTELLIGIBLE"]
    dramatic_purpose: Text | None = None

    @model_validator(mode="after")
    def require_fragment_purpose(self) -> "LinePlayability":
        if self.fragmentation != "CONTINUOUS" and not self.dramatic_purpose:
            raise ValueError("UNRESOLVED: fragmentation requires its dramatic purpose")
        return self
