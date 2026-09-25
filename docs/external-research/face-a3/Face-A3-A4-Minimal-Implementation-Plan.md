# Face A3 — A4 Minimal Implementation Plan

DESIGN ONLY · NON_RUNTIME · NOT_IMPORTED · NOT_REGISTERED

基线：2026-09-25，HEAD `3b286cca94ad3a1683060d4df2a986a6f789236f`。全部建议尚未实施；知识成熟度至多 LOCAL_EXPERIMENTAL，媒体效果 NOT_PLATFORM_VALIDATED。

## 决定

**READY_FOR_FACE_A4 = YES**，仅限本文设计清楚的opt-in知识语义、来源消费和QC实现。没有媒体效果验证，没有授权本轮实施。**JOINT_CINEMATOGRAPHY_FACE_A4 = RECOMMENDED**，共享D2、source mapper、reference职责与离线验收可一次实现，避免双重来源链。知识和媒体因果验证仍分开。

## 未来逐文件最小清单

| 文件（相对repo） | Face A4拟改动 | 与摄影关系 |
|---|---|---|
| plugin/skills/specialized-asset-design/SKILL.md | 本profile的face/age/skin/hair/marks单一位置、未知与阶段界限 | 共享C15/C28，合并一个语义段 |
| plugin/skills/specialized-asset-design/references/face-knowledge.json（拟新增） | 35条独立表述的版本化知识目录、scope、source、rule hash；各条owner仍按本设计，不拥有事实或prompt | Face独立知识资料；不注册新Skill |
| plugin/skills/performance-casting/SKILL.md | F27结构对比与F20年龄证据限制；选角非正式资产第二作者 | Face独立 |
| plugin/skills/reference-strategy/SKILL.md | carry/exclude、可见性、覆盖引用与三图真实绑定 | 共享C15 |
| plugin/skills/look-continuity/SKILL.md | baseline vs 当前妆/伤/汗/疲劳；不反写身份 | Face独立 |
| plugin/skills/shot-production/SKILL.md | F30–F40证据/用途/repair路由；无自动retry | 共享C17/C36 |
| plugin/skills/shot-production/references/production-rules.md | 细项观察与既有Review处置对接 | 共享QC |
| plugin/docs/professional-departments.md | Reference/QC开放values profile和唯一owner表 | 共享 |
| plugin/src/drama_plugin/visual/frame_request.py | 只实现共享CINE_D2，不增加Face字段 | 共享一次 |
| plugin/src/drama_plugin/visual/still_knowledge.py（拟新增） | canonical leaves/coverage/duty/source receipt校验与纯映射 | 共享模块，一套operation/receipt/版本规则 |
| plugin/src/drama_plugin/hosts/route_production.py | 现有reserve/begin-submission做opt-in current/approval重验 | 共享；不改route/provider/预算 |
| plugin/tests/test_still_knowledge.py（拟新增） | face范围、mixed leaf拒绝、映射/pins/职责/未知覆盖、证据不出prompt | 共享测试模块，Face独立cases |
| plugin/tests/test_route_image_inputs.py | 三图绑定/槽/hash与旧请求回放、来源变更拒绝 | 共享 |
| plugin/tests/test_visual_prompt_ir.py | static/edit实际可达；age/hair preserve；reason/QC隔离 | 共享 |

这不是要求修改上述所有文件中的无关代码。Face无需修改 contracts/specialized_asset.py、contracts/production_design.py、contracts/professional.py、contracts/visual_prompt.py、visual/image_serializer.py、visual/prompt_ir.py、visual/production.py；无需registry/DAG新owner、Director变更、Provider/MCP/Service/Storage变更。摄影独立D1相关 specialized_asset contracts/host/sourceMap、professional.py既有global-style元数据及cinematography/lighting/color相关skills沿其A3清单；不能借联合名义把Face事实写进D1。

## 冲突风险与顺序

主要风险：两个mapper版本/receipt格式；face描述混入imaging；reference同actor重复键；old/edit输出变化；把knowledge pin当人物source；批准阶段或current race；用漂亮/粗糙评真实。处理顺序：

1. 先合并唯一profile/source receipt规范，确认35 Face ADAPT与16摄影ADAPT各自范围，拒绝同事实重复作者。
2. 先D2空值字节兼容与source重验，再纯mapper；摄影D1独立提交及测试，不做全库迁移。
3. 在同一mapper内加Face语义覆盖、reference duty及source投影，用离线虚构测试数据测试机制（不能把测试角色当A5真实fixture）。
4. 接两个Host recheck点，验证stale/forged/wrong Work/arc/slot顺序失败；既有请求不opt-in即全字节相同。
5. 加QC证据profile，检查MAJOR/UNKNOWN/MINOR处置无变化、无自动retry。
6. 运行现有资产/专业/reference/IR/route相关离线测试及新增实质边界用例。检查单一writer、no-provider-call、未改变transport/model/params。没有A5图像证据不得升级知识成熟度。

只允许已批准profile显式启用，不自动改既有批准角色。选定用途必需知识在static/edit不可达必须fail closed，不能“未来再说”却进入生成。若实施必须改变Director、第二writer、route、MCP/Service/Storage、安装Skill、Video或刻板规则，即触发STOP回报；目前设计未触发。现有规则deprecate清单为空，没有外部winner证据。

## FACE_A4_READINESS_MATRIX

Contract sufficient YES/SEMANTIC表示现有承载结构足够、profile仍需实现；不是当前端到端能力完成。Runtime Change指未来且不等于新增schema。每项A4 Ready不代表A5 Ready。

| Capability | Canonical Owner | Current Contract Sufficient | Runtime Change Needed | Validation Needed | A4 Ready |
|---|---|---|---|---|---|
| F01 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；记录批准人物差异；不统一瓜子脸或理想比。 | YES |
| F02 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；比例是人物事实的描述轴，不是三等分达标线。 | YES |
| F03 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；眉毛、眼睑、阴影不能替代骨骼；未知不补。 | YES |
| F04 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；保留独立关系，拒绝高颧必瘦脸。 | YES |
| F05 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；只吸收关系描述；不吸收饱满才美的规范。 | YES |
| F06 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；方窄圆钝均可；无英雄下颌默认。 | YES |
| F07 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；不能用尖等于前伸；不使用理想角度。 | YES |
| F08 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；开合受当前表演影响；跨角度比较不得直接比像素宽。 | YES |
| F09 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；自然毛发生长与眉妆、眉间紧张分开。 | YES |
| F10 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；拒绝统一高细鼻梁。 | YES |
| F11 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；不把笑容、描唇与当前张口写成稳定形态。 | YES |
| F12 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；外部只支持保存/检查，不提供完整耳部设计或测量法。 | YES |
| F13 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；遮帽区域重建是提案，不能声称还原了未知真实发际线。 | YES |
| F14 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；保留批准密度长度；不普遍加碎发、灰发或头屑。 | YES |
| F15 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；受光颜色不是基础肤色；不按族裔或角色身份自动填色。 | YES |
| F16 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；按年龄、肤况、妆、景别、光线判断可见度；不要求每张都见毛孔。 | YES |
| F18 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；来源和批准决定其是否长期/阶段性；不能为真实感随意添加。 | YES |
| F20 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；外部仅部分线索；没有跨年龄可靠映射、通用皱纹数量或年龄估计器。 | YES |
| F23 | reference-strategy | YES / SEMANTIC | 既有values职责profile + 共享D2/mapper | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；不清楚/遮挡即不可确认；不把参考图暗部推成结构事实。 | YES |
| F24 | reference-strategy | YES / SEMANTIC | 既有values职责profile + 共享D2/mapper | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；光影可能伪装深眼窝/颧点，观察不等于已批准事实。 | YES |
| F25 | reference-strategy | YES / SEMANTIC | 既有values职责profile + 共享D2/mapper | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；多视图是待检查的证据，不是任意角度永不漂移保证；不生成。 | YES |
| F27 | performance-casting（候选比较）；specialized-asset-design（正式身份） | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；吸收结构比较目的；不保证纯文字选项不同等于成像不同。 | YES |
| F29 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；保留职责拆分；固定高光位置不是身份，不吸收 universal 半哑光。 | YES |
| F30 | visual-continuity-qa | YES / SEMANTIC | QC evidence profile，现有Review容器 | 适用/遮挡UNKNOWN、具体证据、唯一repair owner、无自动retry；脸形、眼距、鼻唇与 approved anchor 比；透视表情差异先控制。 | YES |
| F31 | visual-continuity-qa | YES / SEMANTIC | QC evidence profile，现有Review容器 | 适用/遮挡UNKNOWN、具体证据、唯一repair owner、无自动retry；未来候选 QC-AGE-DRIFT；本轮不注册；不能从噪声或肤亮断言变年轻。 | YES |
| F32 | visual-continuity-qa | YES / SEMANTIC | QC evidence profile，现有Review容器 | 适用/遮挡UNKNOWN、具体证据、唯一repair owner、无自动retry；检查未授权瘦颌、大眼、改鼻、磨平年龄与辨识细节。 | YES |
| F33 | visual-continuity-qa | YES / SEMANTIC | QC evidence profile，现有Review容器 | 适用/遮挡UNKNOWN、具体证据、唯一repair owner、无自动retry；结合批准真人媒介、妆态、光照与局部证据，不以有没有瑕疵一刀切。 | YES |
| F34 | visual-continuity-qa | YES / SEMANTIC | QC evidence profile，现有Review容器 | 适用/遮挡UNKNOWN、具体证据、唯一repair owner、无自动retry；形态、反射、重复结构/牙齿漂移；不让更亮更清等于更真实。 | YES |
| F35 | visual-continuity-qa | YES / SEMANTIC | QC evidence profile，现有Review容器 | 适用/遮挡UNKNOWN、具体证据、唯一repair owner、无自动retry；遮挡合理性、额外耳廓、边界失真；不可见用 UNKNOWN。 | YES |
| F36 | visual-continuity-qa | YES / SEMANTIC | QC evidence profile，现有Review容器 | 适用/遮挡UNKNOWN、具体证据、唯一repair owner、无自动retry；与人物身份和当前视角比；非方颌/尖颌达标。 | YES |
| F37 | visual-continuity-qa | YES / SEMANTIC | QC evidence profile，现有Review容器 | 适用/遮挡UNKNOWN、具体证据、唯一repair owner、无自动retry；角色版本与当前整理/遮挡分开，不将新造发际线当已知。 | YES |
| F38 | visual-continuity-qa | YES / SEMANTIC | QC evidence profile，现有Review容器 | 适用/遮挡UNKNOWN、具体证据、唯一repair owner、无自动retry；位置侧别在可见条件下比较；看不清不判消失。 | YES |
| F39 | visual-continuity-qa | YES / SEMANTIC | QC evidence profile，现有Review容器 | 适用/遮挡UNKNOWN、具体证据、唯一repair owner、无自动retry；C15 细化到脸形身份与 pose/gaze/expression/light/camera 来源；D 非验证方法。 | YES |
| F40 | shot-production / Production Review | YES / SEMANTIC | QC evidence profile，现有Review容器 | 适用/遮挡UNKNOWN、具体证据、唯一repair owner、无自动retry；吸收修复范围原则；禁止外部检查失败即自动调用。 | YES |
| F54 | specialized-asset-design | YES / SEMANTIC | 语义知识 + 共享source mapper，不增Face字段 | whole-leaf来源/范围/批准、static/edit消费、A5逐维观察；仅保存 source/approved design 事实；不将化妆视觉效果反写骨相。 | YES |

A5真实fixture尚未选择和批准实验；这不阻断设计到离线实现的准备度，也不授予媒体实验或A4执行权。**本轮STOP。**
