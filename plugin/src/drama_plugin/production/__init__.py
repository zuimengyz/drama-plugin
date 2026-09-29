"""Target ProductionAssembly T2: shadow preparation only, no Prompt or Provider."""
from drama_plugin.production.assembler import ShotAssembler
from drama_plugin.production.capability import ProductionPackageCapability, assembly_workflow
from drama_plugin.production.contracts import (
    AssemblyBoundary, AssemblyIssue, AssemblyIssueCode, AssemblyResult, AssemblyValidation,
    DomainReference, GenerationIntent, PackageContent, PackageScope, ProductionPackage,
    SourceDomain, SourceOwner, SourceReference,
)
from drama_plugin.production.sources import AssemblySources, LegacyAssemblySources
from drama_plugin.production.store import ProductionPackageStore

__all__ = ["AssemblyBoundary", "AssemblyIssue", "AssemblyIssueCode", "AssemblyResult",
    "AssemblySources", "AssemblyValidation", "DomainReference", "GenerationIntent",
    "LegacyAssemblySources", "PackageContent", "PackageScope", "ProductionPackage",
    "ProductionPackageCapability", "ProductionPackageStore", "ShotAssembler", "SourceDomain",
    "SourceOwner", "SourceReference", "assembly_workflow"]
