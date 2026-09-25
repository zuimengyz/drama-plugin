# Face A0 — External Source Freeze

审计日期：2026-09-25（Asia/Shanghai）。本轮仅 Face A0–A2R；所有候选均未安装、未实施、未作平台媒体验证。

## 范围与冻结方法

四个仓库只读 clone 到 `/private/tmp/face-audit-sources/{A,B,C,D}`，未进入 skills 安装目录、未运行外部脚本。冻结完整 git 历史；C 仅研究 `skills/character-design` 四文件及必要的根许可证声明、路径历史。未扩展审计其它 fal skill，未加载 genmedia/model-routing 执行流程。

本地 HEAD：`8f805217f9b7b692a10f3ec0a5363a938f91b192`。开始时 tracked tree clean，已有 `?? docs/`；冻结 835 个 tracked 文件、32 个既有 external-research 文件。见 [local-baseline](evidence/local-baseline.json)。

GitHub API issues 使用 `state=all&per_page=100`；四来源返回数均少于 100，当前页已穷尽该接口结果；includes PR，不能把总数称为 bug 数。issues 是检索时快照，不与源码 commit 假装同时。原始 remote、全量文件清单、相关路径 SHA256、checkout 和状态见 [external-freeze](evidence/external-freeze.json)，原始 API 与 history 在 evidence。

| 来源 | 仓库 / remote | branch | commit SHA | commit date | 可达 commits | issues+PR 返回数 |
|---|---|---|---|---|---|---|
| A | [snowfrost/ai-character-designer](https://github.com/snowfrost/ai-character-designer) | main | 4b531c9e1b429562504ad7ec1db3e20b27df79f5 | 2026-09-12T08:13:40+08:00 | 19 | 0 |
| B | [lovstudio/professional-portrait-skill](https://github.com/lovstudio/professional-portrait-skill) | main | 923523b861e20b88544706e83b2a8e0726fc5542 | 2026-08-24T00:53:01+08:00 | 7 | 0 |
| C | [fal-ai-community/skills](https://github.com/fal-ai-community/skills) | main | 9ca850412943251fc9a466c4c29fdaf7a303a3d8 | 2026-05-13T21:10:57+01:00 | 41 | 25 |
| D | [Shinning1010/realportrait-ai](https://github.com/Shinning1010/realportrait-ai) | main | 35728411922ddf83c612612bc4d2d1c6df8a94a0 | 2026-05-16T15:14:09+08:00 | 1 | 0 |

## Validation classification

| 来源 | classification | confidence（分类／效果） | license | 证据与限制 |
|---|---|---|---|---|
| A | EXTERNAL_CANDIDATE | 高／低 | NO_LICENSE_FOUND；API license=null | 14 tracked files、19 commits；结构知识丰富但混审美模板。无图片文件、无质量测试。四图一致文字声称不可复核。 |
| B | EXTERNAL_CANDIDATE | 高／仅单案例有限支持 | MIT；Copyright 2026 Skill Publisher | 有四阶段同一案例板和质量表，但缺独立图、参数、分母、失败集及多角度验证。不能外推原创设计。 |
| C | EXTERNAL_CANDIDATE | 高／低 | LICENSE_DECLARED_MIT_NOTICE_INCOMPLETE | 根 README 写 MIT；根及 character-design 无 LICENSE；fal-redesign 的 LICENSE 不自动覆盖本目录。与前轮 SHA 相同。 |
| D | REFERENCE_ONLY | 高／未验证 | MIT；Copyright 2026 Shinning | 7 tracked files、1 commit；仅职责说明和文字使用例；无配对媒体及质量数据。 |

分类 confidence 表示对本次证据等级判定的把握，不是成功概率。没有 VALIDATED_EXTERNAL；不因 GitHub、stars、论文链接、精美示例或 CI 存在升级。

## 每来源取证记录

### A — 原创人物提示词设计

重点路径：SKILL、character_card_template、aesthetics、structure_and_makeup、engineering、realism_vs_refined、prompt_craft、academic、generate.py；其余 theory/prompt_standards/candid_snapshot 仅用于识别模板偏好和范围污染。来源行锚点见 [source-index](evidence/source-index.json)。

依赖：静态生成脚本为 Python；可选 API 分支导入 requests；默认 RunningHub 分支委托本机另一个 skill 脚本；并混入 MERJIC、ima 材料、Foyege 课件和 nuyoah 派生知识。它们不是全部已冻结的独立验证来源。candid_snapshot 明写原 skill 未公开、由文章示例逆向蒸馏，不能称已审计原 skill。未进入视频依赖。

维护：未 archived/disabled；最后更新 2026-09-12。history 展示六段皮肤、参考图分支、翻译校验及结构拆分的迭代；是改动证据，不是质量改善实验。`structure_and_makeup` 文件含自测问题与阈值免责声明，非自动测试。generate.py 有静态检查，并非媒体测量器。

生产证据：prompt_craft §12 声称 2026-09-12 四张保持一致；engineering 声称多角度可靠；theory 声称创作者产量。仓库没有对应媒体、调用记录、逐项评分或失败分母。本轮均标 SELF_REPORTED_UNVERIFIED。issues 全状态空数组不代表无失败。仓库公开可读不等于已证实开源许可。许可证未找到，未来不能直接拷贝代码/长模板；候选仅保留问题与独立改写知识，不作法律授权推断。

### B — 既有真人照片精修

重点路径：SKILL、references/prompts、quality-gate、cases/cases.json、PNG、CHANGELOG、skill.yaml、.github/workflows/validate.yml。依赖宿主看图和 raster edit；声明 skill-runtime/v1 与外部 reusable CI workflow。未安装、未执行 CI，CI 配置不能证明人脸质量。

维护：7 commits，最后 2026-08-24（增加反馈门）；2026-07-29 提交案例板。README 有 example.com 占位安装链接，cases cover 指向 skill-publisher namespace，与当前 lovstudio remote 不同；本轮实际查看的是被冻结仓库内 PNG。

已目视查看 1920×1080 四阶段板：可见同一构图近似的人像被逐步提亮、肤质修饰、去帽补发、改变背景与光照。板上多个变量同时变动，不能分离身份保持、磨皮、光照或发型的贡献；遮帽区域没有真实毛发对照。只能认定存在发布的过程展示，不能作身份识别或逐像素不变证明。没有跨年龄、多角度、批量身份漂移评估。README 的授权公开声明是作者声明，本轮不进一步验证个人授权。

### C — character-design 交叉核对

目标只有四个 Markdown 文件；examples 是文本，不是生成结果。anchor、variable、QC 清单存在；表情表与多视图是建议用途，非验证过的媒体集。路径历史只有重构/平铺等记录，没有面部质量实验。仓库 25 条 issues/PR 中出现其他 skill、站点与执行流程声称，不能借作 character-design 同任务证据。依赖 genmedia/model-routing 仅记录为排除项，不读其实现、不执行。

### D — 参考职责文字来源

目标 SKILL 与 usage-examples；README/INSTALL/agents metadata 只用于依赖/完整性。依赖 Codex 图像工具，无独立模型或测试程序。肖像身份与场景职责分离表述明确，但其默认让 scene image 供应表情/姿态、相机与光照，在本平台需要部门授权。默认 iPhone 风格不等于电影真人通用规律。

## Validation evidence ledger

| 证据类型 | A | B | C | D |
|---|---|---|---|---|
| same-person before/after | 未附图 | 一张四阶段组合板；原始各图未附 | 无 | 无 |
| 身份保持 | 四张一致文字声称 | 有限示例，无可重复参数 | anchor 规则 | 职责规则 |
| 多角度 | 模板，无成片 | 无 | turnaround 模板 | 无 |
| 脸结构比较 | 五人文字结构表 | 无几何测量 | 文字 examples | 无 |
| paired generation / A/B | 未发现受控结果 | 顺序精修不是受控 A/B | 无 | 无 |
| 真实生产用途 | 自述，未独立证实 | 一个发布案例 | 目标 skill 未见 | 未见 |
| 失败案例 | 蜡像/漂移等文字清单 | failure 列，无失败图片 | drift 条目，无媒体 | stop 条件，无媒体 |
| 修订历史 | 19 commits | 7 commits + changelog | 41 repo commits；目标路径历史有限 | 1 commit |
| 质量评估 | 作者检查清单 | full frame + crop 检查表 | quality bar | 主观验收措辞 |
| 测试 | 无测试套件；静态 validator | 外部 reusable CI；非图像质量测试 | 目标无测试；索引脚本不证明质量 | 无 |

## 学术依赖核对（仅查 A 自称的背书）

- [Bernal 等 2024 原文摘要](https://pubmed.ncbi.nlm.nih.gov/39525174/)研究三个工具按“传统吸引力”提示生成的样本与美学比例差异；不能推出所有模型默认“当代平均脸”，更不能验证本 skill 或当前生成器。
- [Wei 等原论文](https://link.springer.com/article/10.1007/s10044-021-00975-z)研究吸引力特征预测与 AR 测量；不是身份保真、演员真实感或提示词干预实验。
- [JMIR 2026](https://www.jmir.org/2026/1/e95452/)标题/出版条目可核对，正文网页被 JavaScript 验证阻挡；本轮不声称完成全文核验，也不接受 A 对“四角体系”的验证推论。

本审计不建立医学、法医学或人口群体脸部标准；文献背书不能绕过 same-task/same-medium 验证门槛。
