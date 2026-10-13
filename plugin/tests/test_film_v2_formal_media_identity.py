import hashlib

import pytest

from drama_plugin.contracts.media import Media
from drama_plugin.execution.contracts import MediaIdentity
from drama_plugin.execution.formal_media import FormalMediaStore
from drama_plugin.runtime.contracts import RuntimeScope
from drama_plugin.runtime.contracts import (ArtifactReference, CapabilityResult,
    ExecutionRevision, ExternalRepairRecord, RecoveryClass, ResultStatus)


def records(**changes):
    scope = RuntimeScope(work_id='film-work', scene_id='N01', shot_id='N01-K01')
    physical = MediaIdentity(media_id='media:sha256:' + 'a' * 64, content_hash='a' * 64,
                             kind='VIDEO', mime='video/mp4', byte_count=123)
    source = 'target-media:' + hashlib.sha256((scope.work_id + physical.content_hash).encode()).hexdigest()
    record = Media(id='service-file', work_id=scope.work_id, shot_id=None,
                   source_ref=source, media_type='VIDEO', file_size=123,
                   content_hash=physical.content_hash, mime_type='video/mp4',
                   content={'filmStorageVersion': 2})
    return scope, physical, source, record.model_copy(update=changes)


def validate(**changes):
    # Pure identity check: no HTTP, SQL, file import or generation is simulated.
    scope, physical, source, record = records(**changes)
    FormalMediaStore._validate(None, record, scope, physical, source)


def test_film_v2_file_scope_and_legacy_exact_shot_remain_supported():
    validate()
    validate(shot_id='N01-K01', content={})


def test_mislabeled_audio_is_not_accepted_without_physical_mp4_evidence():
    scope, physical, source, record = records()
    physical = physical.model_copy(update={'kind': 'AUDIO', 'mime': 'audio/mp4'})
    record = Media.model_validate({**record.model_dump(), 'media_type': 'AUDIO',
                                   'mime_type': 'audio/mp4a-latm'})
    with pytest.raises(ValueError, match='identity/hash/MIME/size'):
        FormalMediaStore._validate(None, record, scope, physical, source)


@pytest.mark.parametrize('changes', [
    {'work_id': 'other-film'}, {'shot_id': 'N01-K02'}, {'content': {}},
    {'source_ref': 'other-source'}, {'content_hash': 'b' * 64},
    {'mime_type': 'audio/mp4'}, {'file_size': 124},
])
def test_v2_marker_does_not_hide_wrong_owner_or_bytes(changes):
    with pytest.raises(ValueError, match='identity/hash/MIME/size'):
        validate(**changes)


def repair_record(capability):
    return ExternalRepairRecord(cursor=8, capability_key=capability, failed_revision=12,
        failed_result=CapabilityResult(status=ResultStatus.FAILED,
            code='FORMAL_MEDIA_IDENTITY_INVALID', recovery_class=RecoveryClass.HARD_BLOCK),
        decision_ref=ArtifactReference(owner='user-decision', artifact_ref='original-cost-receipt', version=1),
        current=ExecutionRevision(fingerprint='a' * 64, input_fingerprint='b' * 64))


def test_identity_repair_retains_exact_intake_failure():
    record = repair_record('execution.media_intake:v1')
    assert record.failed_result.code == 'FORMAL_MEDIA_IDENTITY_INVALID'


def test_identity_repair_never_reopens_provider_submission():
    with pytest.raises(ValueError, match='exact media intake'):
        repair_record('execution.provider:v1')
