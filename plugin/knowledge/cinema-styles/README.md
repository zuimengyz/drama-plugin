# 电影风格与表达问题

案例正文继续保存在 `../film-craft/cases`，旧链接与按problem检索保持兼容；不复制到风格目录。七个风格目录只是非互斥导航。专业手段正文只保存在 `../shared-techniques`，Production Design、Camera、Lighting等共享使用。

检索顺序由创作问题决定。可按风格浏览，也可从“逐渐发现门外的事情”“等待一个没有回应的人”检索，不必先选运镜。词组到表达目标的别名可检查，检索不提供艺术评分，不自动选镜头。未知词可使用原文查询或显式目标，不冒充通用语义搜索。

```sh
python plugin/knowledge/film-craft/find_cases.py --expression '希望观众逐渐发现门外发生的事情' --limit 6
python plugin/knowledge/film-craft/find_cases.py --style poetic-cinema --discipline LIGHTING --goal distance
python plugin/knowledge/film-craft/find_cases.py --case playtime --case children-of-men --read
```

`limit`是本次阅读量控制，不是每镜必须引用几个案例。匹配顺序是目录顺序，不是推荐名次；Host可以拒绝全部结果。案例来源包括制作采访、机构／发行方资料和明确署名的分析；它们不会自动升级成原片实测或当前模型证据。

正式作者通过已有 `authorContext.craftKnowledge` 或 `professional_context.craftKnowledge` 选择检索问题及caseIds。没有选择就不查询，不增加调用或阻断。完整方法与来源边界由本地reader送入已有作者调用，实际选择进入现有专业字段；来源说明留在作者上下文。

参阅 [应用方法](../../skills/director/references/film-practice.md) 与 [本轮离线证据](../ai-production-evidence/v6-01-04/README.md)。
