# 叙事节奏与文字候选

外置 `~/.config/historical-plugin/drama-plugin.env` 使用唯一键 `rhythm_speed`，仅 `medium` / `fast`。默认 medium，去首尾空白，显式非法值（含空串）报出键名和配置来源。已有合法值保留。它只属于 Plugin；不写入 MCP Host 或 Java env。

```sh
# 叙事节奏：medium / fast；不设置时默认 medium
rhythm_speed=medium
```

`scripts/load-env.sh` 在 source 期间启用 allexport，启动脚本把小写键传入进程；`load_config` 统一解析。`RhythmContextProvider` 装饰现有本地或 HTTP 上下文 Provider，再注册到真正的 `context.build_context` / `context.refresh_context`，故 SDK 和 MCP 同源。有效 `creativeRhythm` 含 `rhythm_speed`、来源与完整语义，不含其他 env。

- medium：自然、紧凑而相对从容，保留必要环境认知、人物观察、动作过程和有意义的停顿，不填充空等或重复搬放。
- fast：较早进入矛盾/有效行动，及时转向结果与下一步；压缩无新信息的准备收拾；在自然可行时让对白、操作和观察并行，令关键细节兼顾人物、事实与关系。

两者不是视频或台词倍速，不统一乘时长系数、不堆“迅速”、不设每镜秒数、动作密度或最低切镜数。必要观众导航、人物立场、工序时间因果和结局保留，不能塞入不自然的并行动作。没有影响剧情、核心动作、重要事实或关键连续性的重大问题即可作为文字候选继续；普通瑕疵备注，Host自主调整。

影视编剧孵化在故事组织阶段消费语义；Work保留事实与主题，Script分配揭示和推进，Episode安排冲突/反应/收尾，Scene组织可演行动和对白，Shot决定切入/切出、声画覆盖及自然估时。全链引用同一上下文语义，不复制一套评分表。节奏不自动决定媒体模型、分辨率、输入模式、预算或声音服务。

## 新修订与恢复

新建上下文不带 `options.creativeRevisionId`，读取本进程已解析配置。保存文字候选时将 `context.creativeRhythm` 原样放在现有 `Work.content.creativeRevisions[修订ID].rhythm`，正文、共同源引用和文本审查同置，采用状态独立保留。没有独立版本实体时使用此开放 content 约定；本地镜号不冒充正式 Shot ID。

恢复传入 `options.creativeRevisionId`，上下文读取正式保存的节奏语义，缺记录时报错，不回退当前 env。已有上下文的 refresh 也保留自身节奏。显式新修订重新 build 才读取新配置。对照实验依次运行隔离进程；不改共享全局 env，不覆盖活动 Script/Scene/Shot 或生产账本。

正文候选中可按任务授权重新措辞，完整列出对白并保留意义与戏剧化来源。它们不是正式 Scene spokenContent 的替代权威；采用前不得覆盖活动对白或生成新媒体。
