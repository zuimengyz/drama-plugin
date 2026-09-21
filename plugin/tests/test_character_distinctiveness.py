"""Text compilation regressions only. Artistic approval is exclusively user-owned."""
from pathlib import Path
from copy import deepcopy
import json
import pytest
from drama_plugin.contracts.base import dump_contract as dump,sha256_canonical as fp
from drama_plugin.contracts.expression import CharacterExpressionProfiles,CastingArchetypeProfile
from drama_plugin.casting_visual_compiler import compile_heroic_visual_intent,DIMENSIONS
P=Path(__file__).parents[1]
I=P/'profiles/instances/gaixia/xiang_yu'

def cases():
    b=CharacterExpressionProfiles.model_validate_json((I/'expression-profiles.json').read_text())
    xi=json.loads((I/'mode-visual-intents.json').read_text())['HERO_CASTING']
    # Same age, same heroic level, identical numerical/category controls; role input alone changes.
    commander=dict(zip(DIMENSIONS,(
      '27–32岁，匀称的职业军人骨架与中等肩腰差，训练过的身体，体量服从军中群体尺度。',
      '27–32岁青年，观察性眼神、平静口线，正在权衡部属报告；威信来自判断与专业信誉。',
      '直立整洁的衣甲轮廓，两臂近身，体量均衡。',
      '双脚平衡分开，躯干端正，手保持规整的待命位置。',
      '低机位全身，空间秩序围绕任务与军中职责组织，不以身体侵占观者空间。',
      '功能性灰色军衣与轻层甲，装饰少，避免扩大体格。',
      '有层次的军营纵深，人物轮廓清楚。',
      '可执行命令的训练有素的准备状态，动作经济。',
      '腰间佩剑入鞘，双手无需握武器；武器表示任务装备。')))
    civilian=dict(zip(DIMENSIONS,(
      '27–32岁，修长而轻的文官身体，细肩和舒展手指，体量不以武力为中心。',
      '27–32岁青年，高位文官的自持与倾听，目光沉静清醒。',
      '层叠织物与窄长侧影，袖口留白使手势清楚。',
      '全身立姿，一手持简牍，一手掌心开放，有分寸的交谈姿态。',
      '斜侧全身，台阶与门框表达社会地位，不放大身体威胁。',
      '青色长袍和织物腰束，无甲胄。',
      '厅堂柱间明暗有纵深，背景从属于人物。',
      '重心平衡，下一刻准备递出文件，手势精确而平和。',
      '无武器，只持轻质简牍。')))
    archetypes=json.loads((P/'config/casting-archetypes.json').read_text())
    out={'B_xiang_yu':(b,xi,CastingArchetypeProfile.model_validate(archetypes['tragic_hero_warlord']))}
    for key,values,arch,position,personality in (
        ('A_great_commander',commander,'tragic_hero_warlord','军中职业指挥者','审慎专业，通过判断获得信任'),
        ('C_civil_official',civilian,'scholar_official','高位文官','自持、倾听、公共责任')):
        raw=dump(b);core=raw['characterCoreProfile'];core.update(identity=key,archetype=arch,personalityCore=[personality],historicalPosition=position,storyFacts=['合成测试，无正式剧情事实'],sourcePins={'synthetic':'a'*64})
        cg=raw['cgExpressionProfile'];cg.update(character=key,coreFingerprint=fp(core),design={'face':values['facialIntensity'],'body':values['bodyProportion'],'costume':values['costumeIconicity'],'posture':values['pose'],'camera':values['camera'],'actionSignature':values['kineticPotential']})
        out[key]=(CharacterExpressionProfiles.model_validate(raw),values,CastingArchetypeProfile.model_validate(archetypes[arch]))
    return out

def results():
    # Deliberately generic style for all three, not a route profile with Xiang Yu settings.
    style={'visualRoute':'stylized_cinematic_cg','visualLanguage':'HEROIC_CINEMATIC_CG','rendering':'Designed cinematic three-dimensional characters','materialPalette':'Functional authored materials','historicalBoundary':'Respect source events and functional physical construction','forbiddenDrifts':['No recognizable game-IP copying or fantasy effects']}
    return {key:compile_heroic_visual_intent(b,'stylized_cinematic_cg','HERO_CASTING',values,style,archetype=arch) for key,(b,values,arch) in cases().items()}

def test_same_capability_and_same_age_distinctive_instance_outputs():
    data=cases();out=results()
    controls=[]
    for b,_,_ in data.values():
        controls.append({k:v for k,v in dump(b.cg_expression_profile).items() if k not in ('character','coreFingerprint','design','revision')})
    assert controls[0]==controls[1]==controls[2]
    assert all('27–32' in d['prompt'] for d in out.values())
    generic=[{r['id']:r['text'] for r in d['segments'] if r['sourceLayer']=='generic_capability'} for d in out.values()]
    assert generic[0]==generic[1]==generic[2]
    # Removing names/core labels still leaves visible relational choices distinct.
    text={k:'\n'.join(r['text'] for r in d['segments'] if r['id'].startswith('intent.')) for k,d in out.items()}
    assert 'BODY FIRST, ARMOR SECOND' in text['B_xiang_yu']
    assert '屈肘主动停在腰前' in text['B_xiang_yu'] and '手腕中立' in text['B_xiang_yu']
    assert '职业军人骨架' in text['A_great_commander'] and '双手无需握武器' in text['A_great_commander']
    assert '无武器，只持轻质简牍' in text['C_civil_official']
    for key in ('A_great_commander','C_civil_official'):
        assert all(x not in text[key] for x in ('项羽','BODY FIRST','thick neck','veteran_general_drift','POWER + MOMENTUM'))
    for dim in DIMENSIONS:
        assert len({values[dim] for _,values,_ in data.values()})==3

def test_instance_anti_drifts_are_scoped_not_global():
    out=results();x=out['B_xiang_yu']['prompt']
    for term in ('veteran_general_drift','senior_commander_drift','mature_marshal_drift','generic_great_commander_drift'):
        assert term in x
        assert all(term not in out[k]['prompt'] for k in ('A_great_commander','C_civil_official'))
    assert 'clean-shaven upper lip and chin' in x and '不咬牙、怒目、冷笑' in x
    assert 'POWER + MOMENTUM + DOMINANCE + DECISIVENESS' in x
    assert '不挥舞、不击打' in x and '已批准R3的CG幅度上限' in x

def test_specific_segments_are_instance_owned_and_reconstructible():
    for d in results().values():
        assert '\n\n'.join(r['text'] for r in d['segments'])==d['prompt']
        for row in d['segments']:
            assert d['prompt'][row['start']:row['end']]==row['text']
            if row['id'].startswith('intent.'):
                assert row['sourceLayer']=='instance'
                assert all(p.startswith('spec.modeVisualIntents.HERO_CASTING.') for p in row['sources'])

def test_character_profile_cannot_enter_live_route():
    from drama_plugin.expression import casting_expression
    b=cases()['B_xiang_yu'][0]
    with pytest.raises(ValueError,match='NO_FALLBACK'):
        casting_expression(b,'live_action_realist','DESIGN_NEUTRAL')
    assert b.live_action_expression_profile is None
