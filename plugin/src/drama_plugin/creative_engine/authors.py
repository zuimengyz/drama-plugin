"""Author primitives only; a capability never selects a following workflow step."""
from typing import Protocol
from drama_plugin.creative_engine.contracts import AuthorRequest, CanonDraft, DesignBody, ShotBody


class CanonAuthor(Protocol):
    async def author(self, request: AuthorRequest) -> CanonDraft: ...


class CreativeDirectionAuthor(Protocol):
    async def author(self, request: AuthorRequest) -> ShotBody: ...


class ProfessionalAuthor(Protocol):
    async def design(self, request: AuthorRequest) -> tuple[DesignBody, ...]: ...


# Native ports have no default model/Host fallback. Existing pure author primitives may
# implement these contracts, explicitly labelled MIGRATION_ONLY by their adapters.
