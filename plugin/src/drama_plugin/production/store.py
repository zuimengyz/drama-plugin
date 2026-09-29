"""IN_MEMORY_TEST_FOUNDATION: immutable packages and small assembly diagnostics."""
from __future__ import annotations

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.production.contracts import AssemblyValidation, ProductionPackage
from drama_plugin.runtime.contracts import ArtifactReference


class ProductionPackageStore:
    durability = "IN_MEMORY_TEST_FOUNDATION"
    creative_authority = False

    def __init__(self) -> None:
        self._packages: dict[str, ProductionPackage] = {}
        self._validations: dict[str, AssemblyValidation] = {}

    def put(self, package: ProductionPackage) -> ArtifactReference:
        package = ProductionPackage.model_validate(package.model_dump())
        previous = self._packages.get(package.package_id)
        if previous is not None and previous != package:
            raise ValueError("Immutable package identity conflict")
        self._packages[package.package_id] = package
        return package.artifact_reference()

    def get(self, reference: ArtifactReference) -> ProductionPackage:
        if reference.owner != "production-package" or reference.version != 1:
            raise ValueError("Not a production package reference")
        return self._packages[reference.artifact_ref]

    def retain_validation(self, validation: AssemblyValidation) -> ArtifactReference:
        validation = AssemblyValidation.model_validate(validation.model_dump())
        identity = "assembly-validation:" + sha256_canonical(validation)
        self._validations[identity] = validation
        return ArtifactReference(owner="assembly-validation", artifact_ref=identity, version=1)

    def validation(self, reference: ArtifactReference) -> AssemblyValidation:
        if reference.owner != "assembly-validation" or reference.version != 1:
            raise ValueError("Not an assembly validation reference")
        return self._validations[reference.artifact_ref]
