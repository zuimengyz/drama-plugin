from copy import deepcopy
import pytest
from test_visual_prompt_ir import visual_ir, fact
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.visual.prompt_ir import compile_ir, verify_compilation


def compiled(ir, **kw):
    return compile_ir(ir, provider_family='Flux.2 [pro]', **kw)


@pytest.mark.parametrize('task', ['TEXT_TO_IMAGE', 'FIRST_FRAME', 'KEY_FRAME'])
def test_initial_is_a_visible_target_not_an_edit_or_internal_dump(task):
    ir=visual_ir(task); before=deepcopy(ir)
    result=compiled(ir); p=result['prompt']
    for forbidden in ['CRITICAL','IMPORTANT','SECONDARY','subject.','blocking.','edit_delta',
                      'source_issue','preserve existing','MUST CHANGE','Correct ','Replace ','Remove ']:
        assert forbidden not in p
    for text in ['TARGET WORLD','SUBJECTS','CURRENT BLOCKING','ENVIRONMENT','CAMERA','LIGHTING','TARGET LOOK',
                 '19th century','Petersburg','38–42 years old','old wool coat','man left, girl right','eye level']:
        assert text in p
    assert ir==before and fp(result['ir'])==result['ir_fingerprint']
    assert result['ir']['action']['non_current']==before['action']['non_current']
    verify_compilation(result,p)


def test_edit_is_delta_first_and_does_not_reauthor_full_bibles():
    ir=visual_ir('IMAGE_EDIT'); before=deepcopy(ir)
    ir['continuity']=[fact('shoe crack visible')]
    before=deepcopy(ir)
    result=compiled(ir); p=result['prompt']
    assert p.startswith('MUST CHANGE\n')
    assert p.index('Correct man face') < p.index('PRESERVE') < p.index('TARGET RESULT')
    assert 'Replace right background' in p and 'modern parking sign' in p
    assert before['preserve'][0]['text'] in p
    assert '19th century' in p and 'Petersburg' in p and 'Live-action cinematic still.' in p
    # Face and garment anchors are required identity/clothing preservation,
    # not the whole character Bible (hair, body and surface detail stay in IR).
    assert 'narrow long face' in p and 'old wool coat' in p
    for text in ['short dark brown hair','ordinary narrow shoulders','minor wear on stone','shoe crack visible',
                 'CRITICAL','IMPORTANT','SECONDARY','edit_delta[','subject.man','continuity[']:
        assert text not in p
    assert ir==before and result['ir']['continuity']==ir['continuity']
    assert any(r['reason']=='EDIT_SOURCE_PRESERVED_NOT_REDESCRIBED' for r in result['omitted'])


def test_edit_budget_never_drops_a_correction_or_preserve_instruction():
    ir=visual_ir('IMAGE_EDIT')
    result=compiled(ir)
    # Even a huge irrelevant optional Bible detail never competes with delta.
    ir['secondary_details']=[fact('unrelated sleeve abrasion '*1000,'SECONDARY')]
    tight=compiled(ir,hard_limit=len(result['prompt']))
    assert tight['prompt']==result['prompt']
    assert 'Correct man face' in tight['prompt'] and 'Replace right background' in tight['prompt']
    assert ir['preserve'][0]['text'] in tight['prompt']
    with pytest.raises(ValueError,match='PROVIDER_PROMPT_BUDGET_EXCEEDED'):
        compiled(ir,hard_limit=len(result['prompt'])-1)


@pytest.mark.parametrize('mode,digest', [
    ('text','6fead7909eb6e7a004117c523ece5b868c5f989761a01763f7e758dbfb64e0fc'),
    ('single_image','285939f8cd0135cf2c8aa703719b824d319ce8006a3fd8f6a05656544e91f860'),
    ('first_last','e79cc06613d0b61bfcca6e3bdb260cb98cc361612c03a4bdd12aabdb8364d69f'),
    ('reference','fd0b95a2920da924a884ce5739a399da31b3cf2a39c092e85372fe4af88f22c8')])
def test_entire_video_compilation_is_byte_equivalent_to_before_change(mode,digest):
    ir=visual_ir('VIDEO'); ir['task']['input_mode']=mode
    assert fp(compiled(ir))==digest
