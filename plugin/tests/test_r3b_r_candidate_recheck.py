"""Frozen unedited R3C candidates: replay is distinct from fresh readiness."""
from r3b_r_helpers import FIXTURE
from r3b_r_recheck import recheck


def test_same_r3_candidate_blockers_and_stale_director_boundary() -> None:
    out=recheck(FIXTURE)
    assert out['inputsUnmodifiedInMemory']
    assert not out['productionAuthorized']
    for sid, scene in out['scenes'].items():
        assert scene['source']['status']=='PASS'
        assert scene['dramaturgy']['value']['status']=='PASS'
        assert scene['mapper']['value']['readyForDirection']
        for findings in scene['listenerSilenceLocal'].values():
            assert findings and all(f['status']=='PASS' for f in findings)
        for turn in scene['turns'].values():
            assert turn['exactTurn']['status']=='PASS'
            assert turn['directionOriginalPinsReplay']['status']=='PASS'
            if sid=='S03':
                assert turn['directionCurrentReceipt']['finding']=='STALE_DIRECTOR_DRAMATURGY'
                assert turn['directorIntentCurrentReceipt']['finding']=='STALE_DIRECTOR_DRAMATURGY'
            else:
                assert turn['directionCurrentReceipt']['status']=='PASS'
                assert turn['directorIntentCurrentReceipt']['status']=='PASS'
