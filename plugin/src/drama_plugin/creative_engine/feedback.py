"""Observed feedback becomes a precise owner request; reviewers never mutate facts."""
from drama_plugin.creative_engine.contracts import Authority, Kind, RevisionRequest, VersionRef
from drama_plugin.creative_engine.store import CreativeVersionStore
from drama_plugin.execution.contracts import CreativeMediaReview
from drama_plugin.runtime.contracts import ArtifactReference

# Canon/Shot authority aliases only. Professional department aliases live in its backend catalog.
CANON_OWNERS = frozenset({"canon-author", "canon", "scene", "work", "screenplay", "screenplay-dialogue"})
DIRECTION_OWNERS = frozenset({"creative-direction-author", "shot", "direction"})


def revision_requests(review: CreativeMediaReview, review_ref: ArtifactReference,
                      refs: tuple[VersionRef, ...], versions: CreativeVersionStore,
                      *, depth: int) -> tuple[RevisionRequest, ...]:
    if review.outcome != "REVISE" or review.artifact_reference() != review_ref:
        raise ValueError("Exact REVISE review required")
    from drama_plugin.professional_design.resolver import professional_owner_domain
    result = []
    for observation in review.observations:
        if not observation.required_revision:
            continue
        if observation.owner in CANON_OWNERS:
            owner, kind, domain = Authority.CANON, Kind.SCENE, None
        elif observation.owner in DIRECTION_OWNERS:
            owner, kind, domain = Authority.DIRECTION, Kind.SHOT, None
        elif professional_owner_domain(observation.owner) is not None or observation.owner == Authority.PROFESSIONAL.value:
            owner, kind = Authority.PROFESSIONAL, Kind.PROFESSIONAL
            domain = professional_owner_domain(observation.owner)
        else:
            raise ValueError("CAPABILITY_ABSENT: unknown feedback owner")
        matches = [ref for ref in refs if versions.resolve(ref).kind == kind and
                   (domain is None or getattr(versions.resolve(ref).body, "domain", None) == domain)]
        if len(matches) != 1:
            raise ValueError("Feedback must identify one referenced creative version")
        result.append(RevisionRequest(owner=owner, target_ref=matches[0], finding_ref=review_ref,
            instruction=observation.required_revision, depth=depth))
    if len(result) != 1:
        # Multiple cross-owner revisions require a bounded coordinator rather than silently dropping observations.
        raise ValueError("REVIEW_REQUIRED: feedback must resolve one owner per revision round")
    return tuple(result)
