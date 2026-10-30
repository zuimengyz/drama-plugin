# 《药》镜头覆盖限额补正

2026-10-30。接续上一轮正式 Director 验证；本轮只重做覆盖，不重做 A/B。

## 原因与修正

上轮由 Codex 在临时实验脚本中主动把有效配置的 `65,536` 覆盖成 `4,096`，试图控制费用，却没有充分估计完整镜头覆盖 JSON 的篇幅。推理才是主要消耗，过低的可见输出硬限额导致了一次本可避免的截断。这是实验设置失误，不是用户配置要求。

本轮删除该覆盖，直接读取配置的 **65,536**。费用通过独立的 $1 新预算、输入估算和推理预留控制；不是将预算问题转化为正文截断。保留 `grok-4.7`、`high` 和官方兼容 API。

真实请求发送前逐字段比较：**除 `max_tokens: 4096 → 65536` 外，所有请求字段完全相同，messages 逐字复用。** 没有修改上游艺术内容，也没有把截断响应或 Host 专业补写作为新答案喂回。

[请求差异证据](/tmp/grok-coverage-complete-20261030/request-difference.json) · [配置快照](/tmp/grok-coverage-complete-20261030/configuration.json) · [预算方法](/tmp/grok-coverage-complete-20261030/budget-policy.md)

## 真实结果

一次真实调用，经过工作区现有：

`FormalDirectionAuthor.direct_film → TextCompositionBackend.complete/_complete → httpx → https://api.x.ai/v1/chat/completions`

成功返回完整 JSON，`finish_reason=stop`，正式作者契约及 Canon 对白权限校验通过。脚本禁止调用 `film_treatment` 和 `scene_treatment`；已选 World、Look、全片方向、单场原稿和选择引用均保持原样。没有用 Host 补完 JSON 或通过 ReplayClient 重放结果。

- [完整镜头覆盖可读版](/tmp/grok-coverage-complete-20261030/complete-coverage.md)：由原始字段直接展示，艺术正文未润色。
- [Grok 原始可见输出](/tmp/grok-coverage-complete-20261030/coverage/original-content.txt) · [原始 SSE](/tmp/grok-coverage-complete-20261030/coverage/raw-response.sse)
- [正式验证后的 FilmDirection](/tmp/grok-coverage-complete-20261030/coverage.json) · [后端诊断](/tmp/grok-coverage-complete-20261030/backend-diagnostic.json)
- [上游复用与原件指纹](/tmp/grok-coverage-complete-20261030/reused-originals.json) · [核对结果](/tmp/grok-coverage-complete-20261030/validation.json)

| 镜头 | 内容 | Grok 估时 | 对白 |
|---|---|---:|---|
| 1 | 暗中起身、点灯，问话与里间咳嗽使注意分开 | 40 秒 | “小栓的爹，你就去么？”、“唔。” |
| 2 | 枕下摸钱、交接、碰袋沿、换握、按两下 | 36 秒 | “你给我罢。” |
| 3 | 点稳灯笼、熄桌灯，光离开母亲；父亲在门口受咳嗽阻住，话后等候 | 50 秒 | “小栓……你不要起来。……店么？你娘会安排的。” |
| 4 | 转身、母亲让路、拔闩、侧身出门、带门 | 22 秒 | 无新对白 |
| 5 | 空街、灯贴腿、背伸直、步幅变化、狗抬头不叫、走远 | 32 秒 | 无新对白 |

合计 **180 秒**，是导演的电影时长估计，不是实际成片长度，也不是五个已合法配置的 Seedance 请求。四句 Canon 对白各绑定一次，没有遗漏或增写对白。

## 承接检查与保留意见

完整覆盖包含开场至街道终点，没有把后续丁字街、刑场或天亮提前搬入。交钱后钱包留在袋里；点灯笼及熄桌灯只发生一次；第4镜门已带上，第5镜从门外继续，不重新出门或关门。母亲坐到铺沿被第4镜明确安排在前一镜门口等待后段，属于已选编剧“已经坐到铺沿”的发展。

两处措辞仍应保留为专业落实前的澄清，不因契约通过就称艺术和连续性完美：

1. 第3镜 `exitState` 写“尚未转身”，第4镜从转身开始；第3镜 `coverage` 又写“他一转身，有用的观看才结束”。应明确剪辑边界究竟落在转身前还是动作中，避免重复。原文未被 Host 擅改。
2. 第3镜行动写“门内……没有人”，结合全稿应指没有可见人物；不能据此把画外病儿从场景世界中删除。既有小栓咳嗽及“始终未露面”仍是本场依据。

具体铺面形制仍未定，固定机位如何兼顾暗铺、门口侧脸、灯位和视场还需专业布局／排演。当前结果是**完整、可读且通过正式作者契约的覆盖候选**，不是已验收摄影、表演或影像。

上轮 Host 第三镜专业稿依据的是截断响应中的 42 秒局部对象。本轮第三镜为新的 50 秒候选；没有把旧专业稿或旧离线 Prompt 自动标成已适配本轮新版本。本轮不扩大到专业重写或媒体生产。

## 用量与边界

| 项目 | 实际值 |
|---|---:|
| 新增 API 请求 | 1 |
| 请求与返回模型 | grok-4.7 |
| reasoning_effort | high |
| 配置输出上限 | 65,536 |
| 输入 Token | 24,100 |
| 实际可见输出 Token | 4,102 |
| 推理 Token | 27,869 |
| 官方 usage 报告费用 | **$0.238298** |
| 未扣缓存的保守计算 | $0.240026 |
| 未知／失败请求 | 0 |

[完整费用账本](/tmp/grok-coverage-complete-20261030/cost-ledger.json)。输出上限不等于实际消费；本次可见输出略超上轮限额，但两次生成不是同一段逐字文本，不能反推上次只缺6个 Token。上轮费用独立保留，本轮未重复计入。

本轮只调整隔离实验脚本并保存报告。没有新增 Plugin／Skill／Runtime／Provider 代码修改；没有创建正式 Work／Run／Scene／Shot 或 ProductionPackage，没有 MySQL／MinIO 写入、归档、媒体生成、发布、重载、commit/push。实验沿用现有临时作用域标签与内存原件，不把候选选择冒充用户正式采纳。

此次没有重跑与限额无关的大批回归；验证采用真实调用、正式后端校验、请求逐字段差异、原件哈希、完整 JSON、对白绑定及整场人工阅读。上一轮截断响应和报告原样保留。本轮到此停止。
