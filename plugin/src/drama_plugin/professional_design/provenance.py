"""System-owned Professional provenance; never infer references from model text."""
from __future__ import annotations

from typing import TYPE_CHECKING
from pydantic import JsonValue, TypeAdapter

from drama_plugin.creative_engine.contracts import DesignBody, Kind, VersionRef, scope_contains
from drama_plugin.runtime.contracts import RuntimeScope

if TYPE_CHECKING:
    from drama_plugin.creative_engine.store import CreativeVersionStore

# Names are exact contract aliases, not fuzzy string matching against identities.
REF_FIELDS = {name: kind for kind in (Kind.SOURCE, Kind.WORK, Kind.SCRIPT, Kind.SCENE, Kind.SHOT)
              for name in (kind.value.lower() + 'Ref', kind.value.lower() + '_ref')}
FLAT_FIELDS = {name: (kind, field) for kind in (Kind.SOURCE, Kind.WORK, Kind.SCRIPT, Kind.SCENE, Kind.SHOT)
               for field in ('identity', 'version', 'fingerprint')
               for name in (kind.value.lower() + field.title(), kind.value.lower() + '_' + field)}
MANAGED_FIELDS = frozenset({'sourcePins', 'source_pins', 'scope', *REF_FIELDS, *FLAT_FIELDS})
ORDER = (Kind.WORK, Kind.SCRIPT, Kind.SCENE, Kind.SHOT, Kind.SOURCE)
JSON: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)


def reject_model_metadata(value: JsonValue) -> None:
    if isinstance(value, dict):
        if MANAGED_FIELDS.intersection(value):
            raise ValueError('PROFESSIONAL_SYSTEM_METADATA_MODEL_OWNERSHIP')
        # Exact structured artifact identities cannot hide under an arbitrary key.
        if 'identity' in value and ('version' in value or 'fingerprint' in value):
            raise ValueError('PROFESSIONAL_SYSTEM_METADATA_MODEL_OWNERSHIP')
        for child in value.values():
            reject_model_metadata(child)
    elif isinstance(value, list):
        for child in value:
            reject_model_metadata(child)


def creative_facts(value: JsonValue) -> JsonValue:
    """Only declared infrastructure fields are excluded; prose remains exact."""
    if isinstance(value, dict):
        return {k: creative_facts(v) for k, v in value.items() if k not in MANAGED_FIELDS}
    if isinstance(value, list):
        return [creative_facts(child) for child in value]
    return value


def authority_metadata(versions: CreativeVersionStore, scope: RuntimeScope,
                       refs: tuple[VersionRef, ...]) -> tuple[list[JsonValue], dict[Kind, JsonValue]]:
    by_kind: dict[Kind, JsonValue] = {}
    for ref in refs:
        artifact = versions.resolve(ref)
        if artifact.kind not in ORDER:
            continue
        if artifact.kind in by_kind or not scope_contains(artifact.scope, scope) or versions.stale(ref):
            raise ValueError('PROFESSIONAL_SOURCE_PIN_AUTHORITY_MISMATCH')
        by_kind[artifact.kind] = JSON.validate_python(ref.model_dump(mode='json', by_alias=True))
    pins = [by_kind[k] for k in ORDER if k in by_kind]
    return pins, by_kind


def project_metadata(design: DesignBody, versions: CreativeVersionStore, scope: RuntimeScope,
                     refs: tuple[VersionRef, ...]) -> DesignBody:
    """Explicit owner projection, used only after model-field rejection or reconciliation."""
    pins, by_kind = authority_metadata(versions, scope, refs)
    scope_value = JSON.validate_python(scope.model_dump(mode='json', by_alias=True))
    def project(value: JsonValue) -> JsonValue:
        if isinstance(value, dict):
            output: dict[str, JsonValue] = {}
            for key, child in value.items():
                if key in ('sourcePins', 'source_pins'):
                    output[key] = pins
                elif key == 'scope':
                    output[key] = scope_value
                elif key in REF_FIELDS:
                    if REF_FIELDS[key] not in by_kind:
                        raise ValueError('PROFESSIONAL_REFERENCE_AUTHORITY_ABSENT')
                    output[key] = by_kind[REF_FIELDS[key]]
                elif key in FLAT_FIELDS:
                    kind, field = FLAT_FIELDS[key]
                    reference = by_kind.get(kind)
                    if not isinstance(reference, dict):
                        raise ValueError('PROFESSIONAL_REFERENCE_AUTHORITY_ABSENT')
                    output[key] = reference[field]
                else:
                    output[key] = project(child)
            return output
        if isinstance(value, list):
            return [project(child) for child in value]
        return value
    facts = project(JSON.validate_python(design.facts))
    assert isinstance(facts, dict)
    facts['sourcePins'], facts['scope'] = pins, scope_value
    return DesignBody(domain=design.domain, facts=facts)


def validate_metadata(design: DesignBody, versions: CreativeVersionStore, scope: RuntimeScope,
                      refs: tuple[VersionRef, ...], *, required: bool = True) -> None:
    expected = project_metadata(design, versions, scope, refs)
    if required and not {'sourcePins', 'scope'} <= design.facts.keys():
        raise ValueError('PROFESSIONAL_SYSTEM_METADATA_ABSENT')
    # Lists may have a historical order; identity/version/hash set must be exact.
    def check(value: JsonValue, projected: JsonValue) -> None:
        if isinstance(value, dict) and isinstance(projected, dict):
            if 'identity' in value and ('version' in value or 'fingerprint' in value):
                raise ValueError('PROFESSIONAL_UNDECLARED_PROVENANCE_FIELD')
            for key, child in value.items():
                wanted = projected[key]
                if key in ('sourcePins', 'source_pins'):
                    try:
                        actual = TypeAdapter(tuple[VersionRef, ...]).validate_python(child)
                        exact = TypeAdapter(tuple[VersionRef, ...]).validate_python(wanted)
                    except ValueError:
                        raise ValueError('PROFESSIONAL_SOURCE_PIN_AUTHORITY_MISMATCH') from None
                    if len(set(actual)) != len(actual) or set(actual) != set(exact):
                        raise ValueError('PROFESSIONAL_SOURCE_PIN_AUTHORITY_MISMATCH')
                elif key == 'scope' or key in REF_FIELDS or key in FLAT_FIELDS:
                    if child != wanted:
                        raise ValueError('PROFESSIONAL_SOURCE_PIN_AUTHORITY_MISMATCH')
                else:
                    check(child, wanted)
        elif isinstance(value, list) and isinstance(projected, list):
            for child, wanted in zip(value, projected, strict=True):
                check(child, wanted)
    check(JSON.validate_python(design.facts), JSON.validate_python(expected.facts))
