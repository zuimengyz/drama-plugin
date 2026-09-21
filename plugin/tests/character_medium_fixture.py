"""Historical-name text fixture; appearances are test inventions, never canon."""
from pathlib import Path
from character_package_fixture import make_package
from drama_plugin.characters.casting import PackageCastingProjection
from drama_plugin.characters.repository import digest
from drama_plugin.contracts.visual_medium import VisualMediumIntent
from drama_plugin.contracts.base import dump_contract


def medium_case(root: Path, medium='CINEMATIC_CG', mode='HERO_CASTING', *, legacy=False):
    root.mkdir(parents=True, exist_ok=True)
    repo, package, ref, _, _ = make_package(root/'repo', status='VISUAL_TESTING',
        identity='韩信（纯文本编译测试；不构成史实外貌复原）',historical_role='汉初将领（纯文本测试标签）',
        routes=('heroic_cinematic_cg','live_action_realist','realistic_cg'))
    directive=root/'directive.txt'; directive.write_text('Offline text compilation only; no media production.')
    route='heroic_cinematic_cg' if medium=='CINEMATIC_CG' else 'live_action_realist'
    intent=VisualMediumIntent(visual_medium=medium, character_treatment='HEROIC',
        realism_level='GROUNDED_STYLIZED', casting_mode=mode)
    texts={
        'core':'角色：韩信；历史人物姓名仅作通用编译样例。以下外观属于测试设计，不是史实复原。成年男性，中等身高，普通成年人体比例。',
        'dramaticIdentity':'神情克制，目光专注；不使用极端表情。人物注意力指向画外听者。',
        'visualExpression':'脸型瘦长，下颌转折清楚，眉弓适度，自然胡茬；肩背与腰腹比例克制。衣物采用历史语境中的布衣与朴素皮革束带，不添加魔幻盔甲或武器。',
        'actionSignature':'双脚支撑稳定，双手可见，身体轻微转向听者；不新增剧情动作。',
        'antiDrift':'保持衣物功能与重力关系；装备不抢人物。避免动漫、卡通、手办和夸张游戏过场人物。',
    }
    raw=dict(characterPackage=ref,route=route,castingMode=mode,framing='FULL_BODY',
        scopeText='单个人物，全身构图，头顶及双脚完整留边，视角克制，背景简洁。',
        directiveRef=str(directive),directiveHash=digest(directive.read_bytes()),
        paragraphs=[dict(key=k,text=v,packagePointers=['/'+k],interpretation='VISUAL_INTERPRETATION_NOT_NEW_CORE') for k,v in texts.items()])
    if not legacy:raw['visualMediumIntent']=dump_contract(intent)
    return repo, package, PackageCastingProjection.model_validate(raw)
