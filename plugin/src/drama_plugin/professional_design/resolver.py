"""The single Target Professional Design read interface; never an author or Gate."""
from __future__ import annotations

from typing import Protocol

from drama_plugin.production.contracts import AssemblyValidation
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

    def __init__(self, backend: ProfessionalDesignBackend) -> None:
        self.backend = backend

    async def resolve(self, request: ProfessionalDesignRequest) -> ProfessionalDesignSelection:
        request = ProfessionalDesignRequest.model_validate(request.model_dump())
        selection = await self.backend.select(request)
        return ProfessionalDesignSelection.model_validate(selection.model_dump())

    async def validate(self, request: ProfessionalReferenceCheck) -> AssemblyValidation:
        request = ProfessionalReferenceCheck.model_validate(request.model_dump())
        validation = await self.backend.validate(request)
        return AssemblyValidation.model_validate(validation.model_dump())
