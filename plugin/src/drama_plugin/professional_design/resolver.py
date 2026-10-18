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
from drama_plugin.contracts.source_pin import SourcePin
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

    async def revise_assets(self, request: AuthorRequest, *, preparation_ref: SourcePin,
                            asset_ids: tuple[str, ...]) -> SourcePin:
        """Ask the existing asset author for an isolated, source-bound candidate."""
        if self.asset_sequence is None:
            raise ValueError('SPECIALIZED_ASSET_SEQUENCE_REQUIRED')
        return await self.asset_sequence.revise_candidate(request, cast('AssetAuthor', self.author),
            preparation_ref=preparation_ref, asset_ids=asset_ids)

    @staticmethod
    def asset_bindings(request: AuthorRequest) -> list[dict[str, JsonValue]] | None:
        sequence = (request.professional_context or {}).get('assetSequence')
        if not isinstance(sequence, dict):
            return None
        from drama_plugin.creative_engine.author_projection import object_value, sequence as sequence_rows
        assets = [object_value(row) for row in sequence_rows(sequence['currentAssets'])]
        return [{**row, 'content': {'specializedAsset': {k:v for k,v in object_value(object_value(row['content'])['specializedAsset']).items()
            if k not in {'designOriginal','adoptionOriginal','scenePreparationOriginal'}}}} for row in assets]

    @staticmethod
    def text_design_refs(request: AuthorRequest, domain: SourceDomain) -> list[dict[str, JsonValue]]:
        """Project provenance only; the receiving Professional still authors the facts."""
        sequence = (request.professional_context or {}).get('assetSequence')
        if not isinstance(sequence, dict):
            return []
        from drama_plugin.creative_engine.author_projection import object_value, sequence as sequence_rows
        rows = [object_value(row) for row in sequence_rows(sequence.get('currentTextDesigns', []))]
        return [{'requirementKey': row['requirementKey'], 'designRef': row['designRef'],
            'handoffRef': row['handoffRef']} for row in rows if domain.value in sequence_rows(row['domains'])]

    @staticmethod
    def continuity_design_refs(request: AuthorRequest, versions: CreativeVersionStore | None = None) -> list[JsonValue]:
        """Exact selected upstream designs, never a lookup of mutable heads.

        Same-Shot currentDesigns are revisable candidates, not their own parents.
        Scene/Work originals are inherited authority and must invalidate reuse.
        """
        from drama_plugin.creative_engine.contracts import DesignBody, Kind, VersionRef
        context = request.professional_context or {}
        refs: list[JsonValue] = []
        for name in ('filmLook', 'locationCandidates'):
            rows = context.get(name, [])
            if isinstance(rows, list):
                if versions is not None:
                    from drama_plugin.contracts.source_pin import SourcePin
                    for row in rows:
                        if (isinstance(row, dict) and 'ref' in row and
                                versions.objects.read_ref(SourcePin.model_validate(row['ref'])) != row.get('design')):
                            raise ValueError('PROFESSIONAL_CONTINUITY_ORIGINAL_MISMATCH')
                refs.extend(row['ref'] for row in rows if isinstance(row, dict) and 'ref' in row)
        rows = context.get('currentDesigns', [])
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict) or 'ref' not in row:
                    continue  # Historical author candidates have no system pin.
                if versions is not None:
                    original = versions.resolve(VersionRef.model_validate(row['ref']))
                    if (original.kind != Kind.PROFESSIONAL or not isinstance(original.body, DesignBody)
                            or row.get('domain') != original.body.domain.value or row.get('facts') != original.body.facts):
                        raise ValueError('PROFESSIONAL_CURRENT_DESIGN_ORIGINAL_MISMATCH')
                    if original.scope == request.scope:
                        continue
                elif isinstance(row.get('facts'), dict) and row['facts'].get('scope') == request.scope.model_dump(mode='json', by_alias=True):
                    continue
                if row['ref'] not in refs:
                    refs.append(row['ref'])
        return refs

    @staticmethod
    def creative_input_fingerprint(request: AuthorRequest) -> str | None:
        """Refresh retained author output when actual selected design text changes."""
        from drama_plugin.contracts.base import sha256_canonical
        context = request.professional_context or {}
        inputs = {key: context[key] for key in ('currentDesigns', 'filmLook', 'locationCandidates', 'assetSequence')
            if context.get(key)}
        return sha256_canonical(inputs) if inputs else None

    def asset_inheritance_current(self, request: AuthorRequest, designs: Iterable[DesignBody],
                                  versions: CreativeVersionStore | None = None) -> bool:
        designs = tuple(designs)
        refs = self.continuity_design_refs(request, versions)
        if any((refs or 'continuityDesignRefs' in design.facts)
                and design.facts.get('continuityDesignRefs', []) != refs for design in designs):
            return False
        bindings = self.asset_bindings(request)
        if bindings is None:
            return True
        sequence = (request.professional_context or {})['assetSequence']
        assert isinstance(sequence, dict)
        for design in designs:
            if design.domain in {SourceDomain.SUBJECTS, SourceDomain.WORLD, SourceDomain.REFERENCE}:
                if (design.facts.get('assetBindings') != bindings
                        or design.facts.get('assetNarrativeRef') != sequence['narrativeRef']):
                    return False
            text_refs = self.text_design_refs(request, design.domain)
            if (text_refs or 'assetTextDesignRefs' in design.facts) and design.facts.get('assetTextDesignRefs', []) != text_refs:
                return False
        return True

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
            if 'assetTextDesignRefs' in item.facts:
                raise ValueError('PROFESSIONAL_SYSTEM_METADATA_MODEL_OWNERSHIP')
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
        if 'assetTextDesignRefs' in design.facts:
            raise ValueError('PROFESSIONAL_SYSTEM_METADATA_MODEL_OWNERSHIP')
        reject_model_metadata(design.facts)
        context = request.professional_context or {}
        refs = self.continuity_design_refs(request, versions)
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
        text_refs = self.text_design_refs(request, design.domain)
        if text_refs:
            design = design.model_copy(update={'facts': {**design.facts, 'assetTextDesignRefs': text_refs}})
        # Current upstream professional versions are real parents. A same-Shot
        # candidate must never become a parent of its replacement identity.
        from drama_plugin.creative_engine.contracts import VersionRef
        parents = {ref.identity: ref for ref in request.source_refs
            if not ((original := versions.resolve(ref)).kind == Kind.PROFESSIONAL and original.scope == request.scope)}
        for ref in refs:
            if isinstance(ref, dict) and 'identity' in ref:
                parent = VersionRef.model_validate(ref)
                parents[parent.identity] = parent
        return versions.write(writer=Authority.PROFESSIONAL, kind=Kind.PROFESSIONAL,
            scope=request.scope, body=design, sources=tuple(parents.values()), operation=operation)


def professional_owner_domain(owner: str) -> SourceDomain | None:
    """Compatibility owner labels are decoded only inside ProfessionalDesign."""
    from drama_plugin.professional_design.catalog import DEPARTMENT_DOMAINS
    return DEPARTMENT_DOMAINS.get(owner)
