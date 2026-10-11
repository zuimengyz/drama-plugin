"""The single Target Professional Design read interface; never an author or Gate."""
from __future__ import annotations

from typing import Protocol, TYPE_CHECKING, cast, Iterable

from pydantic import JsonValue

if TYPE_CHECKING:
    from drama_plugin.creative_engine.authors import ProfessionalAuthor
    from drama_plugin.creative_engine.contracts import AuthorRequest, DesignBody, VersionRef
    from drama_plugin.creative_engine.store import CreativeVersionStore
    from drama_plugin.professional_design.asset_sequence import SpecializedAssetSequence, AssetAuthor

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
        self.asset_sequence: SpecializedAssetSequence | None = None

    async def prepare_assets(self, request: AuthorRequest) -> AuthorRequest:
        if self.asset_sequence is None:
            return request
        return await self.asset_sequence.prepare(request, cast('AssetAuthor', self.author))

    @staticmethod
    def asset_bindings(request: AuthorRequest) -> list[dict[str, JsonValue]] | None:
        sequence = (request.professional_context or {}).get('assetSequence')
        if not isinstance(sequence, dict):
            return None
        from drama_plugin.creative_engine.author_projection import object_value, sequence as sequence_rows
        assets = [object_value(row) for row in sequence_rows(sequence['currentAssets'])]
        return [{**row, 'content': {'specializedAsset': {k:v for k,v in object_value(object_value(row['content'])['specializedAsset']).items()
            if k not in {'designOriginal','adoptionOriginal','scenePreparationOriginal'}}}} for row in assets]

    def asset_inheritance_current(self, request: AuthorRequest, designs: Iterable[DesignBody]) -> bool:
        bindings = self.asset_bindings(request)
        if bindings is None:
            return True
        sequence = (request.professional_context or {})['assetSequence']
        assert isinstance(sequence, dict)
        return all(design.facts.get('assetBindings') == bindings
            and design.facts.get('assetNarrativeRef') == sequence['narrativeRef']
            for design in designs if design.domain in {SourceDomain.SUBJECTS, SourceDomain.WORLD, SourceDomain.REFERENCE})

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
        checked = await self.prepare_assets(AuthorRequest.model_validate(request.model_dump()))
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
        context = request.professional_context or {}
        refs: list[JsonValue] = []
        for name in ('filmLook', 'locationCandidates'):
            rows = context.get(name, [])
            assert isinstance(rows, list)
            refs.extend(row['ref'] for row in rows if isinstance(row, dict))
        if refs:
            design = design.model_copy(update={'facts': {**design.facts, 'continuityDesignRefs': refs}})
        sequence = context.get('assetSequence')
        if isinstance(sequence, dict) and design.domain in {SourceDomain.SUBJECTS, SourceDomain.WORLD, SourceDomain.REFERENCE}:
            bindings = self.asset_bindings(request)
            assert bindings is not None
            design = design.model_copy(update={'facts': {**design.facts, 'assetBindings': bindings,
                'assetNarrativeRef': sequence['narrativeRef']}})
            locations = [r for r in bindings if r['assetType'] == 'LOCATION']
            if design.domain == SourceDomain.WORLD and len(locations) == 1:
                design = design.model_copy(update={'facts': {**design.facts, 'locationAssetId': locations[0]['id']}})
        return versions.write(writer=Authority.PROFESSIONAL, kind=Kind.PROFESSIONAL,
            scope=request.scope, body=design, sources=request.source_refs, operation=operation)


def professional_owner_domain(owner: str) -> SourceDomain | None:
    """Compatibility owner labels are decoded only inside ProfessionalDesign."""
    from drama_plugin.professional_design.catalog import DEPARTMENT_DOMAINS
    return DEPARTMENT_DOMAINS.get(owner)
