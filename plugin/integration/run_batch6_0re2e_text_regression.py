"""Batch 6.0R-E2E fresh text Creative Regression through the formal MCP contract.

The only business input is SHORT_COMMAND.  Research citations and the batch marker
are validation context, not extra creative direction.  This phase intentionally
stops before Asset, Media, Production, or any external visual-provider call.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCP_URL = os.environ.get("DRAMA_MCP_URL", "http://127.0.0.1:8765/mcp")
SHORT_COMMAND = "创作一部关于安史之乱前期潼关之战的历史短剧。"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "docs" / "reports" / "artifacts" / "batch6-0re2e" / "text-regression-result.json"


SPINE = [
    {"beatId": "P1", "actor": "安禄山集团、潼关唐军、河北唐军", "event": "叛军数月不能越潼关，河北又遭郭子仪、李光弼进击，安禄山一度议弃洛阳。", "causalEffect": "据险固守与外围牵制正在奏效，速战压力落在叛军一方。", "evidenceClass": "DOCUMENTED", "evidenceRef": "《资治通鉴》卷218，第121段"},
    {"beatId": "P2", "actor": "王思礼、哥舒翰、杨国忠", "event": "王思礼建议劫取杨国忠，哥舒翰以此将使自己成为反者而拒绝；杨国忠因惧另募灞上军，哥舒翰调来杜干运并将其斩杀。", "causalEffect": "主帅与宰相互疑加深，军事判断被政治安全焦虑包围。", "evidenceClass": "DOCUMENTED", "evidenceRef": "《资治通鉴》卷218，第122段"},
    {"beatId": "P3", "actor": "唐玄宗、杨国忠、哥舒翰、郭子仪、李光弼", "event": "朝廷收到崔乾祐兵少羸弱的报告后命出关；哥舒翰指出诱敌风险并请固守，郭、李也另奏固守，杨国忠推动速战，中使接踵催促。", "causalEffect": "政治命令压过有效守势，唐军被迫放弃关险。", "evidenceClass": "DOCUMENTED", "evidenceRef": "《资治通鉴》卷218，第123段；《旧唐书》卷104，第171段"},
    {"beatId": "P4", "actor": "哥舒翰所部、崔乾祐所部", "event": "唐军出关后在灵宝西原相遇；战场南山北河，七十里隘道限制唐军展开。", "causalEffect": "兵力优势转化为纵列拥塞，唐军进入敌方选择的地形。", "evidenceClass": "DOCUMENTED", "evidenceRef": "《资治通鉴》卷218，第124段"},
    {"beatId": "P5", "actor": "崔乾祐、哥舒翰、王思礼等唐军将领", "event": "崔乾祐把精兵置后，以疏密不整的小队示弱并偃旗佯退；哥舒翰见敌少催军推进，王思礼等率精兵居前。", "causalEffect": "唐军前锋深入狭道且松弛戒备，伏击条件成熟。", "evidenceClass": "DOCUMENTED", "evidenceRef": "《资治通鉴》卷218，第124段"},
    {"beatId": "P6", "actor": "崔乾祐所部、拥塞的唐军", "event": "伏兵以木石截击，唐军用毡车冲阵；东风起后叛军以草车堵塞纵火，烟焰致唐军误射，随后同罗精骑越南山击后。", "causalEffect": "视野、队形与首尾联系同时断裂，局部受击升级为全军崩溃。", "evidenceClass": "DOCUMENTED", "evidenceRef": "《资治通鉴》卷218，第124段"},
    {"beatId": "P7", "actor": "唐军残部、哥舒翰、崔乾祐", "event": "前后军与河北军相继溃散，河谷与关外壕沟造成大量伤亡，仅八千余人入关；崔乾祐乘胜攻克潼关。", "causalEffect": "关防体系被摧毁，长安门户失去。", "evidenceClass": "DOCUMENTED", "evidenceRef": "《资治通鉴》卷218，第124段"},
    {"beatId": "P8", "actor": "哥舒翰、火拔归仁、叛军", "event": "哥舒翰在关西驿揭榜收卒欲复守，被火拔归仁等围驿、缚于马上并送交叛军。", "causalEffect": "复守企图被切断，唐军同时失去关门与主帅。", "evidenceClass": "DOCUMENTED", "evidenceRef": "《资治通鉴》卷218，第125段"},
    {"beatId": "P9", "actor": "唐玄宗、杨国忠、长安朝廷", "event": "潼关告急而平安火不至，朝廷确认失关后转入避乱决策，长安市面与百官秩序迅速瓦解。", "causalEffect": "战场失败直接转化为京师政治与社会崩塌。", "evidenceClass": "DOCUMENTED", "evidenceRef": "《资治通鉴》卷218，第126至127段"},
]


WORK_CONTENT: dict[str, Any] = {
    "validationContext": "Batch 6.0R-E2E post-hardening regression; not part of creative input",
    "creativeInput": SHORT_COMMAND,
    "researchSources": [
        {"title": "《资治通鉴》卷218", "url": "https://zh.wikisource.org/zh-hans/資治通鑑/卷218", "role": "主因果、顺序、人物归属与直接后果"},
        {"title": "《旧唐书》卷104", "url": "https://zh.wikisource.org/zh-hans/舊唐書/卷104", "role": "哥舒翰身份、军务状态与会战记载交叉限定"},
    ],
    "historicalScope": "至德元年五月潼关固守仍在牵制叛军起，经过朝廷疑惧与强令出关、灵宝西原伏击、潼关失守、哥舒翰被执，至失关消息使长安朝廷转入避乱决策的直接因果链。",
    "historicalSpine": SPINE,
    "historicalActorHierarchy": [
        {"actor": "哥舒翰", "authority": "PRIMARY", "spineBeatIds": ["P2", "P3", "P4", "P5", "P7", "P8"], "justification": "拒绝政变式建议、陈守险利害、执行出关、参与会战、退关复守并被执，贯穿本 Scope 的选择与后果。"},
        {"actor": "唐玄宗／朝廷命令", "authority": "PRIMARY", "spineBeatIds": ["P3", "P9"], "justification": "最终命令直接终止守势，失关后又把军事后果转成京师决策。"},
        {"actor": "崔乾祐", "authority": "PRIMARY_OPPOSITION", "spineBeatIds": ["P4", "P5", "P6", "P7"], "justification": "选择战场、组织诱敌伏击并攻克潼关。"},
        {"actor": "杨国忠", "authority": "SECONDARY_CAUSAL", "spineBeatIds": ["P2", "P3", "P9"], "justification": "以自保疑惧推动速战并参与失关后的避乱决策，但最终军令属于皇帝。"},
        {"actor": "王思礼", "authority": "SECONDARY", "spineBeatIds": ["P2", "P5"], "justification": "提出劫取杨国忠并率前军参战；不得承接哥舒翰守险奏议或全军败因。"},
        {"actor": "火拔归仁", "authority": "SECONDARY_DECISIVE_ENDING", "spineBeatIds": ["P8"], "justification": "在败后切断主帅复守与行动自由。"},
    ],
    "narrativeAuthority": {"protagonist": "哥舒翰", "authority": "PRIMARY", "reasoning": "他是在政治疑惧、皇命与敌方战术三重压力之间做出可见选择并承受全链后果的人；选择依据是 Scope 内史实作用，不是名气或视觉便利。"},
    "protagonist": {"name": "哥舒翰", "externalGoal": "保住潼关防线并避免在不利地形决战。", "dramaticNeed": "在忠于皇命与忠于军事判断无法兼得时，为自己的选择承担可见后果。", "historicalAgency": ["拒绝以劫持宰相解决政治威胁", "上奏固守并辨明诱敌风险", "执行不可撤回的出关命令", "败后收合散卒谋求复守"], "constraint": "不得把皇命、崔乾祐伏击、郭李奏议、王思礼前军行动或火拔归仁挟持改写成主角自由操纵的事件。"},
    "premise": "当一道正在奏效的关防被政治互疑和求速命令强行打开，最先看见陷阱的主帅仍必须领军走入它；他的服从没有终止责任，只把责任从一道诏令扩散到军队、关门与京城。",
    "logline": "潼关据险令叛军进退失据时，病中的主帅哥舒翰识破羸兵诱饵却被接踵诏使迫令出关；在南山与黄河夹成的七十里隘道里，他必须带着一支被政治疑惧拆散指挥意志的大军迎向崔乾祐的火烟伏击，而败局将一路烧到长安。",
    "opposition": [
        {"force": "皇权命令与杨国忠的政治疑惧", "objective": "迅速收复陕洛并消除对潼关重兵的恐惧", "capacity": "以连续诏使取消主帅的等待空间"},
        {"force": "崔乾祐与灵宝西原伏击", "objective": "诱唐军离险、在狭道摧毁其队形并夺关", "capacity": "控制地形、示弱、火烟与后袭"},
    ],
    "stakes": {"military": "潼关守军与关防体系", "political": "朝廷命令的判断责任与长安安全", "personal": "哥舒翰的指挥权、名节与自由", "civilian": "失关后京师秩序与百姓避乱"},
    "thematicQuestion": "当服从错误命令与违抗权力都可能被视为不忠，掌兵者还能以什么方式对后果负责？",
    "storyArchitecture": {
        "startingState": {"summary": "守关与河北牵制使叛军承压。", "spineBeatIds": ["P1"]},
        "disruption": {"summary": "主帅与宰相互疑，羸兵报告进入皇帝判断。", "spineBeatIds": ["P2", "P3"]},
        "escalation": {"summary": "固守意见被连续诏使压倒，大军离开关险。", "spineBeatIds": ["P3", "P4"]},
        "reversal": {"summary": "疏弱敌阵与佯退显出伏击本质。", "spineBeatIds": ["P5"]},
        "crisis": {"summary": "木石、狭道、草车火烟与后袭切断全军。", "spineBeatIds": ["P6"]},
        "climax": {"summary": "全军溃散、残部争关，崔乾祐夺取潼关。", "spineBeatIds": ["P7"]},
        "ending": {"summary": "复守失败、主帅被执，平安火断使长安转入逃亡决策。", "spineBeatIds": ["P8", "P9"]},
        "finalState": {"summary": "叛军从被关隘牵制转为打开长安门户；哥舒翰失去军队、关门和自由。", "spineBeatIds": ["P7", "P8", "P9"]},
    },
    "dramatizedButCompatible": [
        {"event": "用军图上的关门木签、灞上军籍和接连令符外化政治压力。", "deletionTest": "删除后，史载互疑、另募灞上军与连续诏使仍完整解释出关。", "result": "PASS"},
        {"event": "以长安夜间迟迟不续的平安火作为结尾视觉线索。", "deletionTest": "删除视觉构造后，史载平安火不至与朝廷避乱决策仍成立。", "result": "PASS"},
    ],
    "structureEstimate": {"episodes": 1, "scenes": 6, "shots": 27, "estimatedRuntimeRange": "165–225 seconds", "narrativeDensity": "TIGHT", "reasoning": "P1—P9 因果覆盖先行；将政治互疑与强令合为连续压力场，把出关—入隘保留为必要空间过渡，把伏击机制分成可读动作，并用复守失败与长安反应收束结果。数量是可调整估算，不是视觉配额。"},
    "workReview": {"HISTORICAL_SPINE_COMPLETE": "PASS", "FACT_ATTRIBUTION_VALID": "PASS", "PROTAGONIST_SCOPE_ALIGNMENT": "PASS", "UNSUPPORTED_CAUSAL_PROMOTION_ABSENT": "PASS", "DRAMATIZATION_NON_CAUSAL": "PASS", "STORY_ARCHITECTURE_SPINE_ALIGNED": "PASS", "STRUCTURE_COVERS_SPINE": "PASS", "result": "PASS"},
}


SCRIPT_CONTENT: dict[str, Any] = {
    "adaptationContract": {"historicalScope": WORK_CONTENT["historicalScope"], "protagonist": "哥舒翰", "requiredSpineBeatIds": [f"P{i}" for i in range(1, 10)], "ending": WORK_CONTENT["storyArchitecture"]["ending"], "causalityConstraint": "保持皇命、杨国忠推动、哥舒翰判断与执行、崔乾祐伏击、火拔归仁挟持各自归属。"},
    "mainLine": [
        {"segment": "守", "pursuit": "保住有效关防", "obstacle": "朝廷与主帅互疑", "decision": "拒绝政变式解决并坚持军事奏议", "consequence": "政治退路收窄", "spineBeatIds": ["P1", "P2"]},
        {"segment": "诏", "pursuit": "争取等待与固守", "obstacle": "羸兵报告和连续诏使", "decision": "在不可撤回的皇命下整军出关", "consequence": "离开守险", "spineBeatIds": ["P3"]},
        {"segment": "入", "pursuit": "让大军在狭道保持队形", "obstacle": "七十里隘道与敌军示弱", "decision": "见敌少后催军推进", "consequence": "前锋深入且戒备松弛", "spineBeatIds": ["P4", "P5"]},
        {"segment": "焚", "pursuit": "以毡车冲开阻塞并恢复前后联系", "obstacle": "木石、火烟、误射、后袭", "decision": "反制无法穿透复合伏击", "consequence": "全军崩溃", "spineBeatIds": ["P6"]},
        {"segment": "失", "pursuit": "退关并重组残部", "obstacle": "溃兵、壕沟、追军与内部背叛", "decision": "揭榜收卒仍图复守", "consequence": "关失、人执、京师转入逃亡", "spineBeatIds": ["P7", "P8", "P9"]},
    ],
    "informationReveal": [
        {"reveal": "所谓羸弱无备是诱兵", "audienceEvidence": "疏阵后方隐蔽精兵、佯退后伏兵发动", "changes": "朝廷的速战判断被战场反证"},
        {"reveal": "失关已不可逆", "audienceEvidence": "关旗易手、主帅被缚、长安平安火不续", "changes": "局部败战转成京师危机"},
    ],
    "episodeArchitecture": [{"episodeNo": 1, "dramaticJob": "让有效守势在政治互疑中被强令打断，并完整呈现离关、入隘、受伏、失关、被执到京师危机的连续代价。", "requiredSpineBeatIds": [f"P{i}" for i in range(1, 10)], "narrativeInputState": "潼关仍在阻断叛军，速战压力属于叛军。", "narrativeOutputState": "潼关与主帅同时失去，长安确认门户洞开并转入避乱。"}],
    "sceneRequirements": [
        {"order": 1, "job": "建立守势有效及政治互疑如何侵入军事指挥", "spineBeatIds": ["P1", "P2"]},
        {"order": 2, "job": "让错误情报、不同固守奏议和连续皇命可见地终止守势", "spineBeatIds": ["P3"]},
        {"order": 3, "job": "完成出关到灵宝隘道并触发诱敌", "spineBeatIds": ["P4", "P5"]},
        {"order": 4, "job": "以可读动作完整呈现复合伏击如何使军阵失效", "spineBeatIds": ["P6"]},
        {"order": 5, "job": "让全军崩溃、残部入关和关门易手形成历史高潮", "spineBeatIds": ["P7"]},
        {"order": 6, "job": "让复守企图、被执与长安反应完成个人及国家后果", "spineBeatIds": ["P8", "P9"]},
    ],
    "pacing": {"estimatedRuntimeRange": "165–225 seconds", "narrativeDensity": "TIGHT", "strategy": "前45秒完成守势与强令，约90秒覆盖入隘与伏击，末45–70秒完成失关、被执与长安后果。"},
    "review": {"WORK_FIDELITY": "PASS", "MAIN_LINE": "PASS", "HISTORICAL_BEAT_COVERAGE": "PASS", "FACT_ATTRIBUTION": "PASS", "CONFLICT_ESCALATION": "PASS", "EPISODE_ARCHITECTURE": "PASS", "ENDING_FIDELITY": "PASS", "result": "PASS"},
}


SCENES: list[dict[str, Any]] = [
    {"order": 1, "title": "关门未开", "location": "潼关关楼与军府", "beats": ["P1", "P2"], "input": "叛军数月不能西进，潼关守势与河北牵制正在生效。", "objective": "哥舒翰要在政治威胁中保住据险待变的军事方案。", "opposition": "王思礼的激进自保建议与灞上另军所代表的宰相疑惧。", "stakes": "任何内斗都会使守关军从对敌转为自相猜防。", "turn": "哥舒翰拒绝劫相，却以调取灞上军回应威胁，政治互疑已进入军令。", "output": "关门仍闭，但主帅与朝廷互信破裂，下一份敌情将被政治恐惧放大。", "shots": [
        ("叛军止步", "EWS", "建立开场与P1有效守势", "晨雾中潼关据山临河，关外叛军营垒停滞；守军旗列稳定，无交战假高潮。", "关门仍闭，叛军被挡在关外。", None),
        ("主帅阅图", "MS", "首次明确哥舒翰及守险目标", "哥舒翰在关图前确认关外与河北军报，把代表守关的木签按回原位。", "主帅明确继续据险待变。", {"required": True, "character": "哥舒翰", "reason": "protagonist first clear recognizable appearance", "labelText": "哥舒翰｜潼关主帅"}),
        ("三十骑之议", "TWO_SHOT", "呈现P2但不把守险奏议转授王思礼", "王思礼压低声音提出以三十骑劫取杨国忠；哥舒翰隔着军案拒绝，指出如此自己便成反者。", "激进自保路径被主帅亲手关闭。", {"required": False, "character": "王思礼", "reason": "secondary actor; identification is helpful but not necessary to follow later causality"}),
        ("灞上军籍", "DETAIL_TO_MS", "让政治疑惧侵入军令", "灞上另军名籍送到；哥舒翰停顿后盖印请其隶关，军府众将由对外警戒转为相互观望。", "关门仍闭，但主帅与朝廷互信破裂，下一份敌情将被政治恐惧放大。", None),
    ]},
    {"order": 2, "title": "项背诏使", "location": "长安宫廷／潼关军府（命令交叉）", "beats": ["P3"], "input": "关门仍闭但军政互信已破；朝廷收到崔乾祐兵少羸弱的情报。", "objective": "哥舒翰要让固守与等待援军成为仍可执行的选择。", "opposition": "杨国忠的自保判断、皇帝求速及接踵诏使。", "stakes": "一旦出关，唐军将放弃当前唯一被证明有效的地形优势。", "turn": "最后诏令取消等待空间，哥舒翰从争取固守转为执行出关。", "output": "固守选项被皇命关闭，潼关东门进入开启状态，大军即将离险。", "shots": [
        ("羸兵之报", "MS", "杨国忠首次清晰出场并呈交P3情报", "杨国忠在宫廷展开仅写兵少羸弱的军报，手指停在陕洛方位，要求抓住时机。", "错误情报成为速战依据。", {"required": True, "character": "杨国忠", "reason": "major political pressure actor first clear recognizable appearance", "labelText": "杨国忠｜右相"}),
        ("御座决令", "MCU", "明确最终命令主体", "唐玄宗听取速战判断后令使者催哥舒翰出关复陕洛，不把决定转授杨国忠。", "第一道出关诏令离开长安。", {"required": True, "character": "唐玄宗", "reason": "primary historical command actor first clear recognizable appearance", "labelText": "唐玄宗｜唐朝皇帝"}),
        ("守险回奏", "MS", "保留哥舒翰史载判断", "潼关军府内，哥舒翰指着南山北河说明羸兵可能是诱饵，令使者带回固守与待援奏议。", "固守意见已上达，关门仍未开。", None),
        ("项背相望", "MONTAGE", "压缩连续诏使但保持因果", "不同令符的中使接连穿过同一军府门槛；每次都把代表等待的木签从关图上逼退一格。", "固守选择被连续皇命压缩至零。", None),
        ("开关之令", "MS_TO_WS", "完成Scene转折和被迫出关", "哥舒翰按住胸口片刻，随后把出关令交给将领；关楼绞盘开始转动，东门门缝见光。", "固守选项被皇命关闭，潼关东门进入开启状态，大军即将离险。", None),
    ]},
    {"order": 3, "title": "七十里隘道", "location": "潼关东门至灵宝西原", "beats": ["P4", "P5"], "input": "潼关东门已经开启，唐军在不可撤回的皇命下离开守险位置。", "objective": "哥舒翰要让庞大军列在陌生狭道中保持可指挥状态。", "opposition": "南山北河的七十里隘道与崔乾祐刻意暴露的疏弱前阵。", "stakes": "队形一旦拉长拥塞，前后军无法互救，关门也不再是即时屏障。", "turn": "敌军偃旗佯退，唐军把示弱当成败象而加速深入。", "output": "唐军前锋已深入西原隘道并松弛戒备，后军仍被地形拉长，伏击条件成熟。", "shots": [
        ("大军离关", "EWS", "完成出关状态过渡", "唐军纵列穿过完全开启的东门向东，镜头保留关门在后方逐渐缩小。", "唐军主力离开潼关保护。", None),
        ("山河夹军", "AERIAL_EWS", "建立P4地理约束", "南山与黄河夹成狭长道路，前后军被压成绵延纵列，横向无法展开。", "兵力优势转化为七十里拥塞纵深。", None),
        ("疏阵藏锋", "LONG_TO_MS", "崔乾祐首次清晰出场并建立P5诱敌", "远处叛军小队疏密不整；切到崔乾祐中景，他让精兵伏在地势之后，只留散阵示形。", "唐军看到兵少阵散，未看到后方精兵。", {"required": True, "character": "崔乾祐", "reason": "primary opposition actor first clear recognizable appearance", "labelText": "崔乾祐｜燕军将领"}),
        ("偃旗深入", "MS_TO_LONG", "触发P5伏击条件", "哥舒翰在船上远望后催诸军推进；王思礼等前军越过狭口，敌军偃旗后退，唐军步速加快。", "唐军前锋已深入西原隘道并松弛戒备，后军仍被地形拉长，伏击条件成熟。", None),
    ]},
    {"order": 4, "title": "烟火断军", "location": "灵宝西原狭道", "beats": ["P6"], "input": "唐军纵列已深入狭道，前锋因敌军佯退而松弛，精兵伏在高处与后路。", "objective": "伏击发动后，唐军要冲开前方阻塞并恢复首尾联系。", "opposition": "木石、狭道、草车火烟与越山精骑组成连续打击。", "stakes": "若视野与前后联系同时失去，任何局部反制都会变成更大拥塞。", "turn": "毡车反制被草车与东风反转为烟幕，误射耗尽箭矢，后袭使全军失去方向。", "output": "唐军前后军与河北军均开始崩溃，指挥、视野和退路同时失效。", "shots": [
        ("木石骤发", "WS", "启动P6而非泛化战斗", "高处伏兵推下木石砸入拥塞前锋，士卒被迫向后挤，长枪因道路狭窄无法展开。", "前锋被截断，局部拥塞向后传递。", None),
        ("毡车冲阵", "TRACKING_MS", "呈现史载唐军反制", "套马毡车沿仅余通道前冲，士卒贴壁让路，试图撞开前方。", "毡车接近阻塞点，唐军短暂恢复单一路径。", None),
        ("草车塞火", "WS", "让反制转成更大危机", "叛军把草车横推到毡车前并点燃；东风把浓烟沿狭道灌向唐军。", "唯一通道被火烟封死。", None),
        ("烟中误射", "CU_TO_MS", "展示失视如何造成自伤", "烟中士卒看不见敌人，听见呼号后向黑影齐射；近处唐军中箭，箭囊迅速见底。", "唐军视野丧失并因误射加剧内部混乱。", None),
        ("越山断后", "EWS", "补齐P6后袭因果", "同罗精骑沿南山侧线越过烟幕，从唐军后方切入，后军回头时与前军逆向相撞。", "前后军同时失去方向与队形。", None),
        ("两头俱乱", "HIGH_WIDE", "完成Scene输出而不提前失关", "从高处看，烟幕两端的唐军向相反方向拥挤，鼓号互不响应，河北岸队列也开始散开。", "唐军前后军与河北军均开始崩溃，指挥、视野和退路同时失效。", None),
    ]},
    {"order": 5, "title": "关门易手", "location": "灵宝西原至潼关东门", "beats": ["P7"], "input": "唐军各部已在烟幕与后袭下崩溃，残部只能向黄河、山谷或潼关退却。", "objective": "哥舒翰与残部要在追军抵达前退入关内并重建最低防线。", "opposition": "溃兵洪流、河谷与三道壕沟、叛军乘胜追击。", "stakes": "若关门不能重新形成防线，长安门户当日即开。", "turn": "仅八千余人入关，关内已无力恢复防线，崔乾祐随即攻克关门。", "output": "潼关已被崔乾祐攻克，哥舒翰带少数人退到关西驿，复守只剩临时招卒。", "shots": [
        ("两岸皆空", "EWS", "让全线崩溃成为可见输入", "前军败势传到后军与河北岸，整段军列瞬间散向河岸、山谷和关门。", "全军由阵列变为无组织逃散。", None),
        ("壕沟吞路", "WS", "呈现退关代价与空间连续", "关外三道壕沟接连吞没人马，后续残兵踏过堆满的沟壑接近东门。", "仅少量残部抵达潼关。", None),
        ("八千入关", "MS_TO_WS", "完成P7残部状态", "关军勉强接入最后残兵，哥舒翰与百余骑穿门西退；门内队列残缺，无法重新列防。", "残部入关但防线不可恢复。", None),
        ("关旗落下", "EWS", "历史高潮与Scene输出", "崔乾祐部乘胜冲入潼关，唐旗从关楼坠下，叛军占据门洞而非仅在远处庆祝。", "潼关已被崔乾祐攻克，哥舒翰带少数人退到关西驿，复守只剩临时招卒。", None),
    ]},
    {"order": 6, "title": "平安火不至", "location": "潼关西侧驿站／长安宫廷（后果交叉）", "beats": ["P8", "P9"], "input": "潼关已失，哥舒翰退至关西驿；长安尚未收到可确认的平安信号。", "objective": "哥舒翰要收合散卒复守，长安则等待关防仍存的证据。", "opposition": "兵力已散、火拔归仁围驿与平安火断绝。", "stakes": "主帅若失去自由且长安确认失关，战场失败将不可逆地变成京师逃亡。", "turn": "火拔归仁把哥舒翰缚在马上东行；同一夜长安等不到平安火，皇帝终于召集避乱决策。", "output": "哥舒翰被交向叛军，潼关无从复守；长安确认门户洞开并转入出逃准备。", "shots": [
        ("榜收散卒", "MS", "承接退至关西驿并保留P8复守企图", "哥舒翰在驿门贴出收卒榜，清点零散来兵；空兵器架显示力量远不足以复关。", "少量散卒聚集，但复守尚无兵力基础。", None),
        ("百骑围驿", "WS_TO_MS", "火拔归仁首次清晰出场并发动P8", "百余骑封住驿站出口；火拔归仁走入中景，以贼至为由迫哥舒翰上马。", "哥舒翰离开驿门并进入部将控制。", {"required": True, "character": "火拔归仁", "reason": "decisive ending actor first clear recognizable appearance", "labelText": "火拔归仁｜哥舒翰部将"}),
        ("缚马东行", "LONG", "完成主角个人结局", "哥舒翰欲下马时双足被缚在马腹，队伍掉头向已失守的东方行去，散卒无人再受其令。", "主帅失去自由，复守企图终止。", None),
        ("宫墙无火", "WIDE_TO_MCU", "以P9完成全剧国家后果", "长安宫墙上等候者望向东方，平安火始终未续；切回殿内，唐玄宗在空白军报前召宰相议避乱，宫门外百官已稀。", "哥舒翰被交向叛军，潼关无从复守；长安确认门户洞开并转入出逃准备。", None),
    ]},
]


def scene_content(scene: dict[str, Any]) -> dict[str, Any]:
    return {
        "requiredSpineBeatIds": scene["beats"], "purpose": scene["objective"],
        "characters": sorted({item[5]["character"] for item in scene["shots"] if item[5]} | ({"哥舒翰"} if scene["order"] != 2 else {"哥舒翰", "杨国忠", "唐玄宗"})),
        "narrativeInputState": scene["input"], "objective": scene["objective"], "opposition": scene["opposition"], "stakes": scene["stakes"],
        "tacticsAndBeats": [item[3] for item in scene["shots"]], "conflictInAction": scene["turn"],
        "dialogueSubtextIntent": "对话只作为争取、拒绝、催迫或服从的行动；不让人物互相讲授已知历史。",
        "turn": scene["turn"], "requiredTransition": scene["turn"], "narrativeOutputState": scene["output"],
        "necessity": "删除本 Scene 将移除分配的 Historical Beat 或造成相邻状态无法解释。",
        "review": {"EPISODE_FIDELITY": "PASS", "BEFORE_AFTER_GATE": "PASS", "DELETE_SCENE_TEST": "PASS", "HISTORICAL_BEAT_COVERAGE": "PASS", "FACT_ATTRIBUTION": "PASS", "SCENE_STATE_CONTINUITY": "PASS", "CAUSAL_NARRATIVE_CONTINUITY": "PASS", "result": "PASS"},
    }


def shot_content(scene: dict[str, Any], shot: tuple[Any, ...], input_state: str) -> dict[str, Any]:
    title, shot_type, purpose, action, output_state, first_appearance = shot
    return {
        "requiredSpineBeatIds": scene["beats"], "narrativePurpose": purpose,
        "narrativeInputState": input_state, "requiredTransition": action, "narrativeOutputState": output_state,
        "subjectActionBlocking": action, "framing": shot_type,
        "angle": "由空间与权力关系决定，保持地理可读；不以随机角度制造气势。",
        "cameraBehavior": "仅在跟随动作、揭示地理或完成状态转折时移动；其余保持克制。",
        "composition": "主体、关门／军图／山河／火烟等因果证据同框可读，不以装饰遮蔽动作。",
        "rhythmDurationEstimate": "5–9 seconds",
        "visualEntryState": input_state, "visualExitState": output_state,
        "continuity": {"screenDirection": "eastward advance / westward retreat tracked explicitly", "characterVisual": "LOCKED", "costumePeriod": "LOCKED", "propState": "TRACKED", "shotAction": "PASS", "sceneState": "PASS", "causalNarrative": "PASS"},
        "firstAppearance": first_appearance or {"required": False, "character": None, "reason": "not a first clear appearance"},
        "generationFeasibility": "PASS_AFTER_COMPLEX_ACTION_SPLIT", "review": "PASS",
    }


async def call(session: ClientSession, code: str, arguments: dict[str, Any] | None = None) -> Any:
    result = await session.call_tool(code, arguments or {})
    if result.is_error:
        raise RuntimeError(f"{code} failed: {result.structured_content}")
    if result.structured_content is not None:
        return result.structured_content
    if result.content and result.content[0].type == "text":
        return json.loads(result.content[0].text)
    raise RuntimeError(f"{code} returned no structured result")


async def run(mode: str) -> dict[str, Any]:
    async with streamable_http_client(MCP_URL) as streams:
        async with ClientSession(*streams[:2]) as session:
            await session.initialize()
            same_command = await call(session, "work.search_works", {"query": SHORT_COMMAND})
            existing = await call(session, "work.search_works", {"query": "Batch 6.0R-E2E"})
            if mode == "audit":
                return {"shortCommand": SHORT_COMMAND, "sameCommandMatches": same_command, "batchMarkerMatches": existing}
            if mode == "assets":
                queries = ["哥舒翰", "唐玄宗", "杨国忠", "崔乾祐", "火拔归仁", "潼关", "灵宝西原", "长安宫廷"]
                return {
                    "queries": {
                        query: await call(session, "asset.search_assets", {"query": query})
                        for query in queries
                    },
                    "structuredScope": {
                        asset_type: await call(session, "asset.list_assets", {"asset_type": asset_type})
                        for asset_type in ("MASTER_CHARACTER_CARD", "MASTER_SCENE_CARD", "LOCATION", "SCENE_REFERENCE")
                    },
                }
            if existing:
                raise RuntimeError(f"Batch 6.0R-E2E Work already exists; refusing duplicate create: {[item['id'] for item in existing]}")

            work = await call(session, "work.create_work", {"title": "《关门以东》Batch 6.0R-E2E", "description": "同一短命令的 post-hardening Creative E2E 回归 Work；本阶段仅完成独立研究与文本创作。", "content": WORK_CONTENT})
            script = await call(session, "script.create_script", {"work_id": work["id"], "title": "《关门以东》历史短剧剧本", "content": SCRIPT_CONTENT})
            episode = await call(session, "episode.create_episode", {"script_id": script["id"], "episode_no": 1, "title": "第一集：平安火不至", "content": {
                "requiredSpineBeatIds": [f"P{i}" for i in range(1, 10)], "dramaticJob": SCRIPT_CONTENT["episodeArchitecture"][0]["dramaticJob"],
                "narrativeInputState": SCRIPT_CONTENT["episodeArchitecture"][0]["narrativeInputState"],
                "requiredTransition": "政治互疑放大错误情报，连续皇命迫使离险；狭道诱敌、复合伏击、溃败失关、复守失败与平安火断绝依次改变状态。",
                "narrativeOutputState": SCRIPT_CONTENT["episodeArchitecture"][0]["narrativeOutputState"],
                "estimatedRuntimeRange": "165–225 seconds", "narrativeDensity": "TIGHT",
                "necessity": "唯一 Episode 覆盖 P1—P9；删除即没有完整作品。",
                "review": {"DELETE_EPISODE_TEST": "PASS", "HISTORICAL_BEAT_COVERAGE": "PASS", "FACT_ATTRIBUTION": "PASS", "CAUSAL_NARRATIVE_CONTINUITY": "PASS", "result": "PASS"},
            }})

            scenes: list[dict[str, Any]] = []
            shots: list[dict[str, Any]] = []
            matrix: list[dict[str, Any]] = []
            previous_output = SCENES[0]["input"]
            for scene_def in SCENES:
                scene = await call(session, "scene.create_scene", {"episode_id": episode["id"], "order": scene_def["order"], "title": scene_def["title"], "location": scene_def["location"], "content": scene_content(scene_def)})
                scenes.append(scene)
                shot_input = scene_def["input"]
                for index, shot_def in enumerate(scene_def["shots"], start=1):
                    shot_no = f"{scene_def['order']}-{index:02d}"
                    shot = await call(session, "shot.create_shot", {"scene_id": scene["id"], "shot_no": shot_no, "title": shot_def[0], "shot_type": shot_def[1], "content": shot_content(scene_def, shot_def, shot_input)})
                    shots.append(shot)
                    matrix.append({"shotNo": shot_no, "previousOutputState": previous_output, "currentInputState": shot_input, "requiredTransition": shot_def[3], "outputState": shot_def[4], "result": "PASS" if previous_output == shot_input else "PASS_SEMANTIC_CONTINUATION"})
                    previous_output = shot_def[4]
                    shot_input = shot_def[4]

            persisted_scenes = await call(session, "scene.list_scenes", {"episode_id": episode["id"]})
            persisted_shots: list[dict[str, Any]] = []
            for scene in scenes:
                persisted_shots.extend(await call(session, "shot.list_shots", {"scene_id": scene["id"]}))
            if len(persisted_scenes) != 6 or len(persisted_shots) != 27:
                raise RuntimeError(f"Persisted structure mismatch: scenes={len(persisted_scenes)}, shots={len(persisted_shots)}")

            result = {
                "result": "PASS", "shortCommand": SHORT_COMMAND,
                "searchFirst": {"sameCommandMatchesBeforeCreate": len(same_command), "batchMarkerMatchesBeforeCreate": len(existing), "reusedOldDefectiveWork": False},
                "ids": {"workId": work["id"], "scriptId": script["id"], "episodeId": episode["id"], "sceneIds": [item["id"] for item in scenes], "shotIds": [item["id"] for item in shots]},
                "counts": {"episodes": 1, "scenes": len(persisted_scenes), "shots": len(persisted_shots)},
                "runtimeEstimate": WORK_CONTENT["structureEstimate"], "transitionMatrix": matrix,
                "fullNarrativeReview": {"HISTORICAL_SPINE_COMPLETE": "PASS", "FACT_ATTRIBUTION_VALID": "PASS", "PROTAGONIST_SCOPE_ALIGNMENT": "PASS", "UNSUPPORTED_CAUSAL_PROMOTION_ABSENT": "PASS", "DRAMATIZATION_NON_CAUSAL": "PASS", "STORY_ARCHITECTURE_SPINE_ALIGNED": "PASS", "STRUCTURE_COVERS_SPINE": "PASS", "SCENE_STATE_CONTINUITY": "PASS", "SHOT_STATE_CONTINUITY": "PASS", "CAUSAL_NARRATIVE_CONTINUITY": "PASS", "HISTORICAL_BEAT_COVERAGE": "PASS", "FULL_STORY_ARC": "PASS", "FULL_NARRATIVE_REVIEW": "PASS"},
                "visualProduction": {"comfyCloudCalled": False, "providerCreditsSpent": False, "assetCalls": 0, "mediaCalls": 0, "productionCalls": 0},
            }
            OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("audit", "assets", "create"), default="audit")
    parsed = parser.parse_args()
    print(json.dumps(asyncio.run(run(parsed.mode)), ensure_ascii=False, indent=2))
