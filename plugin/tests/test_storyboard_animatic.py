"""Synthetic lineage tests, not authored film examples."""
import subprocess
from pathlib import Path
import pytest
from drama_plugin.contracts.sequence import SequencePackage
from drama_plugin.hosts.storyboard_animatic import storyboard_attachment_plan, render_storyboard_animatic
from drama_plugin.hosts.picture_edit import _hash
from test_sequence_production import package


def study(tmp_path):
    p = SequencePackage.model_validate(package())
    boards = {}
    for shot, timing in zip(p.shots, p.editorial.coverage):
        f = tmp_path / (shot.key + '.png')
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                        'color=' + ('red' if shot.key == 'x' else 'blue') + ':s=160x90',
                        '-frames:v', '1', str(f)], check=True)
        boards[shot.key] = [{'path': str(f), 'duration': timing.duration}]
    return p, boards, {pin.key: pin.fingerprint for pin in p.source_pins}


def test_board_change_invalidates_recipe_without_creating_generation(tmp_path):
    p, boards, pins = study(tmp_path)
    first = storyboard_attachment_plan(p, boards, current_fingerprints=pins)
    path = Path(boards['x'][0]['path'])
    path.write_bytes(path.read_bytes() + b'changed-attachment')
    second = storyboard_attachment_plan(p, boards, current_fingerprints=pins)
    assert first['fingerprint'] != second['fingerprint']
    assert first['sequenceFingerprint'] == second['sequenceFingerprint']
    assert second['generationRequests'] == [] and not second['automaticFirstFrame']
    assert not second['productionAuthorized'] and p.production_permission == 'NONE'


def test_changed_owner_and_wrong_coverage_do_not_render(tmp_path):
    p, boards, pins = study(tmp_path)
    pins['s'] = 'b' * 64
    with pytest.raises(ValueError, match='Sequence source'):
        storyboard_attachment_plan(p, boards, current_fingerprints=pins)
    pins['s'] = 'a' * 64
    boards['x'][0]['duration'] += 1
    with pytest.raises(ValueError, match='editorial estimate'):
        storyboard_attachment_plan(p, boards, current_fingerprints=pins)
    boards.pop('y')
    with pytest.raises(ValueError, match='exactly'):
        storyboard_attachment_plan(p, boards, current_fingerprints=pins)


def test_actual_draft_order_ranges_and_unknown_audio(tmp_path):
    p, boards, pins = study(tmp_path)
    before = {key: _hash(Path(value[0]['path'])) for key, value in boards.items()}
    result = render_storyboard_animatic(p, boards, tmp_path / 'preview', current_fingerprints=pins)
    plan = result['pictureEditPlan']
    assert plan['status'] == 'DRAFT' and plan['audioReview'] == 'UNKNOWN'
    assert [e['sourceMedia'] for e in plan['pictureEdit']] == ['x', 'y']
    assert all(e['sourceIn'] == 0 for e in plan['pictureEdit'])
    assert abs(result['render']['duration'] - sum(s.duration for s in p.editorial.coverage)) < .1
    def pixel(t):
        return subprocess.check_output(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', result['render']['output'],
            '-frames:v', '1', '-vf', 'scale=1:1', '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-'])
    red = pixel(.5); blue = pixel(p.editorial.coverage[0].duration + .5)
    assert red[0] > red[2] and blue[2] > blue[0]
    repeated = render_storyboard_animatic(p, boards, tmp_path / 'preview', current_fingerprints=pins)
    assert result['render']['outputHash'] == repeated['render']['outputHash']
    assert before == {key: _hash(Path(value[0]['path'])) for key, value in boards.items()}
    assert result['render']['userAdoption'] == 'UNCHANGED'
