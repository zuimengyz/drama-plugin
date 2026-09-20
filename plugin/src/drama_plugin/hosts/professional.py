"""Host-facing department tasks over existing immutable DirectorArtifactStore.

No provider dependency is imported. The Host delegates creative work to the
registered skill; this adapter validates and retains the returned artifact.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.professional import CreativeBible, DirectorPackage, SceneAssembly, ShotAssembly
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
from drama_plugin.professional import registry, dependency_order, validate_bible, validate_package, bible_pin


class ProfessionalDepartmentHost:
    def __init__(self, root: Path | str, skill_lookup: Callable[[str], Any] | None = None):
        self.store = DirectorArtifactStore(root)
        self.skill_lookup = skill_lookup

    def registry(self) -> list[dict[str, Any]]:
        return [dump_contract(registry()[key]) for key in dependency_order()]

    def _artifacts(self, refs: tuple[SourcePin, ...]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        queue = list(refs)
        while queue:
            ref = queue.pop()
            if ref.key in result:
                if sha256_canonical(result[ref.key]) != ref.fingerprint:
                    raise ValueError('CONFLICTING_DEPENDENCY_REVISIONS')
                continue
            value = self.store.read_ref(ref)
            result[ref.key] = value
            if value.get('schemaVersion') == 'creative-bible-v1':
                bible = CreativeBible.model_validate(value)
                queue.extend(bible.depends_on)
                queue.extend(bible.approval_refs)
            elif value.get('schemaVersion') in ('scene-assembly-v1', 'shot-assembly-v1'):
                queue.append(SourcePin.model_validate(value['sourceRef']))
        return result

    def task(self, department: str, *, task: str, available: Mapping[str, SourcePin], current: Mapping[str, str]) -> dict[str, Any]:
        definition = registry()[department]
        if definition.skill_code and self.skill_lookup:
            self.skill_lookup(definition.skill_code)
        missing = [key for key in definition.depends_on if key not in available]
        stale = [key for key in definition.depends_on if key in available and current.get(available[key].key) != available[key].fingerprint]
        unresolved: list[str] = []
        failed_reviews: list[str] = []
        checked: set[str] = set()
        for key in definition.depends_on:
            if key in available and key not in stale:
                bible = CreativeBible.model_validate(self.store.read_ref(available[key]))
                if bible.created_by_capability != key:
                    raise ValueError('TASK_DEPENDENCY_WRONG_OWNER')
                queue = [bible]
                while queue:
                    dependency = queue.pop()
                    if dependency.id in checked:
                        continue
                    checked.add(dependency.id)
                    if dependency.status == 'DRAFT':
                        unresolved.append(dependency.created_by_capability)
                    if self._failed_review(dependency):
                        failed_reviews.append(dependency.created_by_capability)
                    for ref in dependency.depends_on:
                        if current.get(ref.key) != ref.fingerprint:
                            stale.append(ref.key)
                        else:
                            queue.append(CreativeBible.model_validate(self.store.read_ref(ref)))
        return {'department': department, 'task': task, 'status': 'BLOCKED' if missing or stale or unresolved or failed_reviews else 'READY',
            'dependency': list(definition.depends_on), 'missing': missing, 'stale': stale, 'unresolved': unresolved,
            'failedReviews': failed_reviews,
            'outputRef': None, 'validationStatus': 'NOT_RUN', 'skillCode': definition.skill_code,
            'revisionOwner': department, 'directorMayFillMissingContent': False,
            'automaticDispatch': False, 'providerCalls': 0}

    @staticmethod
    def _failed_review(bible: CreativeBible) -> bool:
        return registry()[bible.created_by_capability].capability_type == 'VALIDATOR' and any(
            r.values.get('deterministic_status') in ('FAIL', 'BLOCKED') or r.values.get('semantic_review_status') == 'FAIL'
            for r in bible.content)

    def submit(self, department: str, bible: CreativeBible, *, current: Mapping[str, str]) -> dict[str, Any]:
        if bible.created_by_capability != department:
            raise ValueError('SUBMISSION_DEPARTMENT_AUTHORITY_MISMATCH')
        definition = registry()[department]
        if definition.skill_code and self.skill_lookup:
            self.skill_lookup(definition.skill_code)
        artifacts = self._artifacts((*bible.depends_on, *bible.approval_refs))
        result = validate_bible(bible, artifacts, current)
        ref = bible_pin(bible)
        self.store.put(ref.key, dump_contract(bible))
        return {**result, 'outputRef': dump_contract(ref), 'task': 'Review professional output',
            'dependency': list(definition.depends_on), 'revisionOwner': department,
            'validationStatus': 'PASS', 'creativeApproval': 'NOT_GRANTED_BY_HOST_VALIDATOR'}

    def retain_assembly(self, assembly: SceneAssembly | ShotAssembly) -> SourcePin:
        key = ('scene-assembly:' + assembly.scene_id if isinstance(assembly, SceneAssembly) else 'shot-assembly:' + assembly.shot_id)
        return self.store.put(key, dump_contract(assembly))

    def retain_package(self, package: DirectorPackage, *, current: Mapping[str, str]) -> dict[str, Any]:
        refs = (*package.bible_refs.values(), *package.scene_assembly_refs, *package.shot_assembly_refs, *package.approval_refs)
        artifacts = self._artifacts(refs)
        result = validate_package(package, artifacts, current)
        ref = self.store.put('director-package:' + package.id, dump_contract(package))
        return {**result, 'directorPackageRef': dump_contract(ref)}

    def dashboard(self, package: DirectorPackage, *, current: Mapping[str, str]) -> list[dict[str, Any]]:
        rows = []
        for department in dependency_order():
            task = self.task(department, task='Maintain owned professional Bible', available=package.bible_refs, current=current)
            ref = package.bible_refs.get(department)
            if ref:
                try:
                    if current.get(ref.key) != ref.fingerprint:
                        raise ValueError('STALE_OUTPUT')
                    bible = CreativeBible.model_validate(self.store.read_ref(ref))
                    result = validate_bible(bible, self._artifacts((*bible.depends_on, *bible.approval_refs)), current)
                    own_failure = self._failed_review(bible)
                    semantic = sorted({str(r.values.get('semantic_review_status')) for r in bible.content if 'semantic_review_status' in r.values})
                    task.update(status='FAILED_REVIEW' if own_failure else 'BLOCKED' if task['status'] == 'BLOCKED' else bible.status,
                        outputStatus=bible.status, outputRef=dump_contract(ref),
                        validationStatus='FAIL' if own_failure else 'BLOCKED' if task['status'] == 'BLOCKED' else result['validationStatus'],
                        contractValidationStatus=result['validationStatus'], semanticReviewStatuses=semantic)
                except ValueError as error:
                    task.update(status='BLOCKED', outputRef=dump_contract(ref), validationStatus='FAIL', conflict=str(error))
            rows.append(task)
        return rows
