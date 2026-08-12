# Drama Plugin

[English](README.md) | **简体中文**

**面向 AI Agent 的历史短剧创作插件。**

Drama Plugin 将历史研究、故事创作、剧本改编、分集开发、场景设计、镜头设计、资产复用和媒体生成组织成一组可被 Agent 使用的 **Skills + Tools**。

它可以被 **Codex、OpenAI Agents SDK 或其他 Agent Host** 加载，让 Agent 根据当前任务自主选择下一步，而不是把创作过程写死成一个固定 Workflow。

你可以把它理解为：

> **给 AI Agent 安装一套“历史短剧创作能力”。**

---

## 它能做什么？

Drama Plugin 当前提供 8 个核心 Skill：

| Skill                 | 用途                    |
| --------------------- | --------------------- |
| `historical-research` | 搜索并核验历史人物、事件、地点和资料    |
| `work-creation`       | 将历史研究结果发展成可影视化的故事作品   |
| `script-adaptation`   | 将作品改编为短剧剧本            |
| `episode-development` | 开发单集内容                |
| `scene-development`   | 设计具体场景                |
| `shot-design`         | 将场景拆解为镜头              |
| `asset-resolution`    | 发现、判断和复用人物、场景、道具等视觉资产 |
| `shot-production`     | 为镜头准备图片、视频、音频等生产任务    |

典型创作过程可以是：

```text
历史研究
   ↓
故事作品
   ↓
影视剧本
   ↓
分集
   ↓
场景
   ↓
镜头
   ↓
资产复用
   ↓
图片 / 视频 / 音频
```

但这**不是固定流水线**。

Agent 可以根据当前任务：

* 从任意阶段开始；
* 回到上游修改已有内容；
* 跳过当前不需要的步骤；
* 查询并恢复之前的创作内容；
* 判断是否复用已有资产；
* 根据 Tool Result 自主决定下一步。

---

## 为什么做 Drama Plugin？

传统 AI 内容生产系统经常把：

```text
Prompt
+
Workflow
+
数据库
+
生成模型
+
业务逻辑
```

绑定在一个系统里。

结果通常是：

* 更换 Agent 很困难；
* 更换生成 Provider 很困难；
* Workflow 越来越庞大；
* Prompt 与业务代码高度耦合；
* 创作逻辑难以复用。

Drama Plugin 选择另一条路线：

> **把创作方法做成 Skill，把能力做成 Tool，把真正的执行交给外部服务。**

因此同一套历史短剧能力可以被不同 Agent Host 使用。

---

## 亮点

### 🧠 Agent 自主决策

Drama Plugin 不要求 Agent 按固定 Workflow 执行。

Agent 根据：

```text
当前 Context
+
当前 Skill
+
可用 Tools
+
Tool Result
```

自行判断下一步。

---

### 🧩 Host Agnostic

核心 Skill 不绑定某一个 Agent 平台。

目标 Host 包括：

* Codex
* OpenAI Agents SDK
* 自定义 Agent Harness
* 其他能够加载 Skills / Tools 的 Agent Runtime

---

### 🔌 外部能力可替换

历史资料、长期记忆、资产系统、图片生成、视频生成和媒体服务都可以由外部 Provider 提供。

当前支持：

```text
Mock
HTTP
```

并为 MCP 集成保留边界。

---

### 🧪 默认可以离线运行

第一次体验 Drama Plugin **不需要数据库、不需要 Java 服务、不需要 ComfyUI，也不需要远程 MCP Server**。

默认使用 Mock Provider + Local Context。

克隆仓库后即可运行测试和示例。

---

### 💾 支持长期创作记忆

Drama Plugin 可以围绕：

```text
Work
Script
Episode
Scene
Shot
Asset
Media
```

恢复并继续已有创作。

这使 Agent 不必每次从零开始生成整个项目。

---

## 5 分钟快速验证

### 1. 获取代码

```bash
git clone https://github.com/zuimengyz/drama-plugin.git
cd drama-plugin/plugin
```

### 2. 创建 Python 环境

要求：

```text
Python >= 3.12
```

macOS / Linux：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. 安装

```bash
python -m pip install -e ".[dev]"
```

### 4. 运行测试

```bash
pytest -ra
```

### 5. 类型检查

```bash
mypy src/drama_plugin
```

### 6. 运行第一个示例

```bash
python examples/build_shot_context.py
```

成功后会看到类似：

```text
Loaded Plugin: drama-plugin 0.1.0
Loaded Skill: shot-production

Context Scope: ...
Shot: ...
Scene: ...
Work: ...
Selected Assets: ...
```

如果这些步骤全部通过，说明：

```text
Plugin
✓

Skills
✓

Mock Providers
✓

Context
✓

核心 Contracts
✓
```

已经可以正常工作。

---

## 怎么使用？

Drama Plugin 有两种主要使用方式。

### 方式一：作为 Agent Plugin 使用

这是推荐方式。

让 Codex 或其他 Agent Host 加载 Drama Plugin。

仓库已经提供：

```text
plugin/.codex-plugin/plugin.json
plugin/skills/
```

Host 加载插件以后，可以根据你的自然语言任务选择对应 Skill。

例如：

```text
研究神龙政变，并基于史实设计一部历史短剧。
```

Agent 可以先使用：

```text
historical-research
```

然后继续：

```text
work-creation
```

再例如：

```text
把这个故事改编成 12 集短剧，每集约 3 分钟。
```

Agent 可以选择：

```text
script-adaptation
episode-development
```

或者：

```text
继续开发第三集，并设计其中第二个场景的镜头。
```

Agent 可以直接进入：

```text
episode-development
scene-development
shot-design
```

你不需要手动指定完整 Workflow。

---

### 方式二：作为 Python Package 使用

也可以直接在 Python 中加载插件：

```python
from drama_plugin import DramaPlugin

plugin = DramaPlugin.load()

print(plugin.manifest.name)

for skill in plugin.skills.list():
    print(skill.code)
```

默认不提供配置文件时，会自动使用本地 Mock 能力。

适合：

* 开发插件；
* 编写测试；
* 验证 Skill；
* 验证 Tool Contract；
* 开发新的 Agent Host Adapter。

---

# 配置

## 零配置模式

第一次运行时什么都不需要配置。

默认配置为：

```yaml
providers:
  memory:
    mode: mock
  asset:
    mode: mock
  research:
    mode: mock
  production:
    mode: mock
  media:
    mode: mock
  context:
    mode: local
```

这意味着所有数据都使用本地测试实现，不会调用外部服务。

---

## 使用配置文件

仓库提供：

```text
plugin/config/drama-plugin.example.yaml
```

复制一份：

```bash
cd plugin

cp config/drama-plugin.example.yaml \
   config/drama-plugin.yaml
```

然后根据需要修改。

例如，只把长期记忆切换到 HTTP 服务：

```yaml
providers:
  memory:
    mode: http

services:
  memory:
    base_url: "http://127.0.0.1:8080"
    timeout_seconds: 10
    operations:
      get_work: "/api/work/get"
      create_work: "/api/work/create"
```

加载：

```python
from drama_plugin import DramaPlugin

plugin = DramaPlugin.load(
    config_path="config/drama-plugin.yaml"
)
```

---

## Provider 配置

当前可以独立配置以下能力：

| Provider     | 本地模式    | 远程模式   |
| ------------ | ------- | ------ |
| `memory`     | `mock`  | `http` |
| `asset`      | `mock`  | `http` |
| `research`   | `mock`  | `http` |
| `production` | `mock`  | `http` |
| `media`      | `mock`  | `http` |
| `context`    | `local` | `http` |

因此可以混合使用，例如：

```text
Memory      → HTTP
Asset       → HTTP
Research    → Mock
Production  → Mock
Media       → HTTP
Context     → Local
```

不需要一次接入所有服务。

---

## HTTP Provider

如果某个 Provider 设置为：

```yaml
mode: http
```

则必须配置对应的：

```yaml
services:
  <service>:
    base_url: "..."
```

例如：

```yaml
providers:
  research:
    mode: http

services:
  research:
    base_url: "http://127.0.0.1:9000"
    timeout_seconds: 10
```

如果服务需要认证：

```yaml
services:
  research:
    base_url: "http://127.0.0.1:9000"
    api_token: "YOUR_TOKEN"
```

推荐不要把 Token 提交到 Git。

---

## 使用环境变量

配置也可以通过环境变量覆盖。

格式：

```text
DRAMA_PLUGIN_PROVIDER_<SERVICE>_MODE

DRAMA_PLUGIN_SERVICE_<SERVICE>_BASE_URL
DRAMA_PLUGIN_SERVICE_<SERVICE>_API_TOKEN
DRAMA_PLUGIN_SERVICE_<SERVICE>_TIMEOUT_SECONDS
```

其中 `<SERVICE>` 可以是：

```text
MEMORY
ASSET
RESEARCH
PRODUCTION
MEDIA
CONTEXT
```

例如：

```bash
export DRAMA_PLUGIN_PROVIDER_MEMORY_MODE=http
export DRAMA_PLUGIN_SERVICE_MEMORY_BASE_URL=http://127.0.0.1:8080
export DRAMA_PLUGIN_SERVICE_MEMORY_API_TOKEN=your-token
```

环境变量优先级高于 YAML。

因此推荐：

```text
YAML
→ 保存非敏感配置

Environment Variables
→ 保存地址覆盖、Token 和部署环境配置
```

---

# Codex / MCP

Drama Plugin 已包含 Codex Plugin manifest，并将 Skill 作为插件能力暴露。

插件包位置：

```text
plugin/
```

Codex manifest：

```text
plugin/.codex-plugin/plugin.json
```

Skills：

```text
plugin/skills/
```

MCP 配置用于连接 Drama Plugin 所需要的外部能力。

如果当前只想体验插件逻辑，**不需要启动 MCP**，直接使用默认 Mock Provider 即可完成快速验证。

如果要连接真实长期记忆、资产系统或生成服务，再根据部署环境配置 HTTP / MCP。

---

# 项目结构

```text
drama-plugin/
│
├── .agents/
│   └── plugins/
│       └── marketplace.json
│
├── plugin/
│   ├── .codex-plugin/
│   ├── skills/
│   ├── src/
│   ├── tests/
│   ├── examples/
│   ├── config/
│   ├── plugin.yaml
│   └── pyproject.toml
│
└── README.md
```

普通使用者主要需要关注：

```text
README
Skills
Configuration
Examples
```

其他目录用于插件实现和测试。

---

# 现在适合用它做什么？

Drama Plugin 目前适合：

* 历史短剧 Agent 原型；
* AI 剧本创作；
* Agent-driven 内容生产；
* Skill / Tool / MCP 集成实验；
* Codex Plugin 实践；
* 长链路 Creative Agent 设计；
* 多 Provider 内容生成系统。

项目目前仍处于早期阶段，接口会继续完善。

核心目标保持不变：

> **让历史短剧创作能力可以独立于具体 Agent、模型、数据库和生成 Provider 被复用。**

---

# Documentation

更详细的插件内部说明：

[`plugin/README.md`](plugin/README.md)

架构说明：

[`plugin/docs/architecture.md`](plugin/docs/architecture.md)

---

# License

MIT

---

## Status

**Current version:** `0.1.0`

Drama Plugin 正在积极开发中。

Issues、建议、测试反馈和贡献都非常欢迎。
