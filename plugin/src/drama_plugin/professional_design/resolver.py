"""The single Target Professional Design read interface; never an author or Gate."""
from __future__ import annotations

from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from drama_plugin.creative_engine.authors import ProfessionalAuthor
    from drama_plugin.creative_engine.contracts import AuthorRequest, DesignBody, VersionRef
    from drama_plugin.creative_engine.store import CreativeVersionStore

from drama_plugin.production.contracts import AssemblyValidation, SourceDomain
from drama_plugin.professional_design.contracts import (
    ProfessionalDesignRequest, ProfessionalDesignSelection, ProfessionalReferenceCheck,
)


class ProfessionalDesignBackend(Protocol):
    async def select(self, request: ProfessionalDesignRequest) -> ProfessionalDesignSelection: ...
    async def validate(self, request: ProfessionalReferenceCheck) -> AssemblyValidation: ...


class ProfessionalDesignResolver:
    role = "REFERENCE_RESOLVER"
    creative_authority = False
    durability = "EPHEMERAL"

    def __init__(self, backend: ProfessionalDesignBackend, *, author: ProfessionalAuthor | None = None) -> None:
        self.backend = backend
        self.author = author

    async def resolve(self, request: ProfessionalDesignRequest) -> ProfessionalDesignSelection:
        request = ProfessionalDesignRequest.model_validate(request.model_dump())
        selection = await self.backend.select(request)
        return ProfessionalDesignSelection.model_validate(selection.model_dump())

    async def validate(self, request: ProfessionalReferenceCheck) -> AssemblyValidation:
        request = ProfessionalReferenceCheck.model_validate(request.model_dump())
        validation = await self.backend.validate(request)
        return AssemblyValidation.model_validate(validation.model_dump())

    async def design(self, request: AuthorRequest) -> tuple[DesignBody, ...]:
        """The unified Professional interface delegates content to its owner primitive."""
        from drama_plugin.creative_engine.contracts import AuthorRequest, DesignBody
        if self.author is None:
            raise ValueError("CAPABILITY_ABSENT")
        checked = AuthorRequest.model_validate(request.model_dump())
        from drama_plugin.professional_design.provenance import reject_model_metadata
        designs = tuple(DesignBody.model_validate(item.model_dump()) for item in await self.author.design(checked))
        for item in designs:
            reject_model_metadata(item.facts)
        return designs

    async def revise(self, request: AuthorRequest) -> tuple[DesignBody, ...]:
        if request.revision is None:
            raise ValueError("Professional revision requires an exact finding/version")
        return await self.design(request)

    def persist(self, versions: CreativeVersionStore, request: AuthorRequest,
                design: DesignBody, *, operation: str) -> VersionRef:
        from drama_plugin.creative_engine.contracts import Authority, Kind
        from drama_plugin.professional_design.provenance import reject_model_metadata
        reject_model_metadata(design.facts)
        return versions.write(writer=Authority.PROFESSIONAL, kind=Kind.PROFESSIONAL,
            scope=request.scope, body=design, sources=request.source_refs, operation=operation)


def professional_owner_domain(owner: str) -> SourceDomain | None:
    """Compatibility owner labels are decoded only inside ProfessionalDesign."""
    from drama_plugin.professional_design.catalog import DEPARTMENT_DOMAINS
    return DEPARTMENT_DOMAINS.get(owner)
