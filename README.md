# Drama Plugin

**English** | [简体中文](README.zh-CN.md)

**An agent plugin for AI-native historical drama production.**

Drama Plugin packages historical research, story creation, script adaptation, episode development, scene design, shot design, asset reuse, and media production into reusable **Skills + Tools** for AI agents.

It can be loaded by **Codex, OpenAI Agents SDK, or other agent hosts**, allowing an agent to decide what to do next instead of following a hard-coded workflow.

Think of it as:

> **A reusable historical-drama production skillset for AI agents.**

---

## What can it do?

Drama Plugin currently provides ten core Skills:

| Skill                 | Purpose                                                                  |
| --------------------- | ------------------------------------------------------------------------ |
| `historical-research` | Research and verify historical people, events, places, and sources       |
| `work-creation`       | Turn historical research into a story suitable for adaptation            |
| `script-adaptation`   | Adapt a Work into a drama script                                         |
| `episode-development` | Develop individual episodes                                              |
| `scene-development`   | Create and refine scenes                                                 |
| `dramatic-performance-direction` | Build replayable Scene/Beat/Line performance direction without modality controls |
| `shot-design`         | Break scenes into cinematic shots                                        |
| `asset-resolution`    | Discover and reuse characters, locations, props, and other visual assets |
| `shot-production`     | Prepare image, video, and audio production for shots                     |
| `audio-production`    | Produce exact-text speech and deterministic final AV                     |

A typical production path may look like:

```text
Historical Research
        ↓
       Work
        ↓
      Script
        ↓
     Episode
        ↓
      Scene
        ↓
       Shot
        ↓
   Asset Reuse
        ↓
Image / Video / Audio
```

But this is **not a fixed workflow**.

An agent may:

* start from any stage;
* revise an upstream object;
* skip unnecessary steps;
* recover previous creative work;
* reuse existing assets;
* decide what to do next from tool results.

---

## Why Drama Plugin?

AI content systems often tightly couple:

```text
Prompts
+
Workflows
+
Databases
+
Generation Models
+
Business Logic
```

That makes it difficult to:

* replace the agent runtime;
* switch generation providers;
* reuse creative logic;
* evolve workflows;
* separate prompts from infrastructure.

Drama Plugin takes a different approach:

> **Creative methods become Skills. Capabilities become Tools. Execution stays behind replaceable services.**

The same domain capability can therefore be used by different agent hosts.

---

## Highlights

### 🧠 Agent-driven

Drama Plugin does not require a predefined workflow.

The agent decides what to do from:

```text
Current Context
+
Current Skill
+
Available Tools
+
Tool Results
```

---

### 🧩 Host agnostic

The core Skills are not tied to a single agent runtime.

Target hosts include:

* Codex
* OpenAI Agents SDK
* custom agent harnesses
* other runtimes capable of consuming Skills and Tools

---

### 🔌 Replaceable capabilities

Historical research, persistent memory, assets, image generation, video generation, and media services can be provided externally.

Current provider modes include:

```text
Mock
HTTP
```

with integration boundaries prepared for MCP-based services.

---

### 🧪 Works offline by default

You do **not** need a database, Java service, ComfyUI instance, or remote MCP server to try Drama Plugin.

The default configuration uses Mock providers and a local Context provider.

Clone the repository and run the tests immediately.

---

### 💾 Long-running creative memory

Drama Plugin can work with persistent creative objects such as:

```text
Work
Script
Episode
Scene
Shot
Asset
Media
```

This allows an agent to continue an existing production instead of regenerating everything from scratch.

---

# 5-minute quick start

## 1. Clone

```bash
git clone https://github.com/zuimengyz/drama-plugin.git
cd drama-plugin/plugin
```

## 2. Create a Python environment

Requirements:

```text
Python >= 3.12
```

macOS / Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

## 3. Install

```bash
python -m pip install -e ".[dev]"
```

## 4. Run tests

```bash
pytest -ra
```

## 5. Run type checks

```bash
mypy src/drama_plugin
```

## 6. Run the example

```bash
python examples/build_shot_context.py
```

A successful run will print output similar to:

```text
Loaded Plugin: drama-plugin 0.1.0
Loaded Skill: shot-production

Context Scope: ...
Shot: ...
Scene: ...
Work: ...
Selected Assets: ...
```

At this point the following core pieces are working:

```text
Plugin
✓

Skills
✓

Mock Providers
✓

Context
✓

Core Contracts
✓
```

---

# How to use it

Drama Plugin can be used in two main ways.

## Option 1 — Use it as an Agent Plugin

This is the recommended model.

Load Drama Plugin from Codex or another compatible agent host.

The repository already includes:

```text
plugin/.codex-plugin/plugin.json
plugin/skills/
```

Once loaded, the host can select Skills based on a natural-language task.

For example:

```text
Research the Shenlong Coup and create a historical short-drama concept grounded in the historical evidence.
```

The agent may start with:

```text
historical-research
```

and continue with:

```text
work-creation
```

Another request might be:

```text
Adapt this story into a 12-episode short drama, with episodes of roughly three minutes each.
```

The agent may use:

```text
script-adaptation
episode-development
```

Or:

```text
Continue episode 3 and design the shots for its second scene.
```

The agent can directly use:

```text
episode-development
scene-development
shot-design
```

The user does not need to manually construct a complete workflow.

---

## Option 2 — Use it as a Python package

Drama Plugin can also be loaded directly:

```python
from drama_plugin import DramaPlugin

plugin = DramaPlugin.load()

print(plugin.manifest.name)

for skill in plugin.skills.list():
    print(skill.code)
```

Without a configuration file, Drama Plugin uses its local Mock capabilities.

This mode is useful for:

* plugin development;
* testing;
* Skill validation;
* Tool contract validation;
* developing new host adapters.

---

# Configuration

## Zero-configuration mode

Nothing needs to be configured for the first run.

The default configuration behaves like:

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

No external service is called.

---

## Configuration file

An example configuration is included at:

```text
plugin/config/drama-plugin.example.yaml
```

Create your own configuration:

```bash
cd plugin

cp config/drama-plugin.example.yaml \
   config/drama-plugin.yaml
```

Then modify only the services you want to replace.

For example, to use a remote persistent-memory service:

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

Load it with:

```python
from drama_plugin import DramaPlugin

plugin = DramaPlugin.load(
    config_path="config/drama-plugin.yaml"
)
```

---

## Provider modes

Each capability can be configured independently:

| Provider     | Local/Test | Remote |
| ------------ | ---------- | ------ |
| `memory`     | `mock`     | `http` |
| `asset`      | `mock`     | `http` |
| `research`   | `mock`     | `http` |
| `production` | `mock`     | `http` |
| `media`      | `mock`     | `http` |
| `context`    | `local`    | `http` |

Mixed configurations are supported.

For example:

```text
Memory      → HTTP
Asset       → HTTP
Research    → Mock
Production  → Mock
Media       → HTTP
Context     → Local
```

You do not need to integrate every service at once.

---

## HTTP providers

When a provider uses:

```yaml
mode: http
```

its corresponding service must have:

```yaml
services:
  <service>:
    base_url: "..."
```

For example:

```yaml
providers:
  research:
    mode: http

services:
  research:
    base_url: "http://127.0.0.1:9000"
    timeout_seconds: 10
```

For authenticated services:

```yaml
services:
  research:
    base_url: "http://127.0.0.1:9000"
    api_token: "YOUR_TOKEN"
```

Do not commit real API tokens.

---

## Environment variables

Configuration may also be overridden through environment variables.

Pattern:

```text
DRAMA_PLUGIN_PROVIDER_<SERVICE>_MODE

DRAMA_PLUGIN_SERVICE_<SERVICE>_BASE_URL
DRAMA_PLUGIN_SERVICE_<SERVICE>_API_TOKEN
DRAMA_PLUGIN_SERVICE_<SERVICE>_TIMEOUT_SECONDS
```

`<SERVICE>` can be:

```text
MEMORY
ASSET
RESEARCH
PRODUCTION
MEDIA
CONTEXT
```

Example:

```bash
export DRAMA_PLUGIN_PROVIDER_MEMORY_MODE=http
export DRAMA_PLUGIN_SERVICE_MEMORY_BASE_URL=http://127.0.0.1:8080
export DRAMA_PLUGIN_SERVICE_MEMORY_API_TOKEN=your-token
```

Environment variables override YAML values.

Deployment values are stored outside Git in
`~/.config/historical-plugin/drama-plugin.env`. When embedded in the MCP Host,
start with `../scripts/start-drama-mcp.sh`; the launcher loads `mcp-host.env`
and `drama-plugin.env`, but never `drama-service.env`. See
[`plugin/docs/runtime-ownership.md`](plugin/docs/runtime-ownership.md).

A practical setup is therefore:

```text
YAML
→ non-sensitive configuration

Environment Variables
→ deployment overrides and secrets
```

---

# Codex / MCP

Drama Plugin includes a Codex plugin manifest and exposes its domain Skills as plugin capabilities.

Plugin package:

```text
plugin/
```

Codex manifest:

```text
plugin/.codex-plugin/plugin.json
```

Skills:

```text
plugin/skills/
```

MCP configuration is used when external Drama capabilities need to be connected to the host.

For the initial experience, **MCP is not required**. The local Mock configuration is enough to run the quick-start validation.

Connect real persistent memory, asset, research, or generation services only when needed.

---

# Repository layout

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

Most users only need to care about:

```text
README
Skills
Configuration
Examples
```

The remaining directories support implementation and testing.

---

# What is it useful for today?

Drama Plugin is currently useful for:

* historical-drama agent prototypes;
* AI script development;
* agent-driven content production;
* Skill / Tool / MCP integration experiments;
* Codex Plugin experiments;
* long-running creative agents;
* multi-provider media-production systems.

The project is still early and interfaces will continue to evolve.

The core goal remains:

> **Make historical-drama production capabilities reusable independently of a specific agent, model, database, or generation provider.**

---

# Documentation

Detailed plugin documentation:

[`plugin/README.md`](plugin/README.md)

Architecture:

[`plugin/docs/architecture.md`](plugin/docs/architecture.md)

---

# License

MIT

---

## Status

**Current version:** `0.1.0`

Drama Plugin is under active development.

Issues, feedback, testing, and contributions are welcome.
