# Drama Plugin

Drama Plugin is a **lightweight, host-agnostic agent plugin layer for AI-native drama production workflows**.

It packages reusable domain Skills, explicit Pydantic contracts, discoverable tool schemas, provider abstractions, and a `Drama Domain -> Model Context` projection API. The goal is to let hosts such as **Codex**, **OpenAI Agents SDK**, or a custom agent harness reuse drama-production capabilities without adopting another heavyweight agent runtime.

> **Drama Plugin does not own the agent loop.**
>
> The host decides when to call the model, which tools to invoke, and how returned context is merged into the next model turn.

Drama Plugin also does **not** implement databases, RAG, asset management, media processing, or image/video generation services. Those remain external capabilities behind explicit provider and tool contracts.

## Why this project exists

Agentic media production often spans many capabilities: project data, assets, historical references, context construction, generation services, and media processing. Putting all of that inside one agent framework creates tight coupling and makes the system harder to audit, test, and replace.

Drama Plugin keeps the integration layer intentionally small:

- **portable Skills** describe domain procedures without owning execution;
- **explicit tool contracts** expose capabilities through stable JSON Schema;
- **provider abstractions** isolate Mock, HTTP, and future MCP integrations;
- **Model Context projection** converts drama-domain data into host-consumable context;
- **host ownership** keeps the agent loop and runtime state outside the plugin.

This makes the plugin useful as a reusable integration boundary rather than a monolithic application framework.

## Architecture

```text
                    Agent Host
       Codex / OpenAI Agents SDK / Custom Harness
                           |
             +-------------+-------------+
             |             |             |
           Skills         Tools      Model Context
             |             |             ^
             |        stable schemas     |
             |             |             |
             +-------- Drama Plugin -----+
                           |
                   Provider Protocols
             +------+------+------+------+
             |      |      |      |      |
           Mock    HTTP   future MCP   local/remote
                           |
                    External Services
```

The architectural boundary is deliberate: the host owns orchestration and model-runtime state; Drama Plugin owns domain contracts, capability discovery, and context projection.

## Core concepts

- **Skill** — a flexible domain SOP with context needs, decision/tool guidance, and completion rules.
- **Tool** — a stable, discoverable external-capability contract with explicit input/output JSON Schema. It contains no service business logic.
- **Provider** — the Mock, HTTP, or future MCP implementation behind a domain tool.
- **ContextBuilder** — projects domain contracts into `DramaModelContext`; it does not manage host runtime context.
- **DramaPlugin** — loads manifests/configuration and composes registries and providers; it runs no LLM loop.

## Design principles

Drama Plugin follows a few strict principles:

1. **Small core** — avoid unnecessary frameworks, abstractions, and runtime ownership.
2. **Host agnostic** — Codex, OpenAI Agents SDK, or another harness can provide orchestration.
3. **Explicit contracts** — tool inputs, outputs, and context structures should be inspectable and testable.
4. **Replaceable integrations** — external capabilities sit behind provider protocols.
5. **Auditable boundaries** — model context, tool execution, permissions, and external responses should cross clear integration boundaries.
6. **Progressive integration** — Mock and HTTP providers work today; MCP can be added without changing Skills.

## Install and verify

Python 3.12 or newer is required.

```bash
python -m pip install -e ".[dev]"

pytest
mypy src/drama_plugin
```

Run the offline demo:

```bash
python examples/build_shot_context.py
```

The default configuration uses coherent Mock providers, so the core can be explored and tested without network dependencies.

## Host Integration PoC

A host can discover the plugin instead of embedding drama-specific orchestration logic:

```python
from drama_plugin import DramaPlugin

plugin = DramaPlugin.load()

skills = plugin.skills.list()
tools = plugin.tools.list()
capabilities = plugin.capabilities()

for tool_code in tools:
    schema = plugin.tools.describe(tool_code)

# The host decides when context should be built and how it enters
# the model runtime.
context = plugin.context.build(...)
```

A Codex, OpenAI Agents SDK, or custom harness can inspect:

```text
plugin.skills.list()
plugin.tools.list()
plugin.tools.describe(code)
plugin.capabilities()
plugin.context.build(...)
```

Host-specific manifest, schema, or tool-registration adapters belong at the integration edge. External services build or return domain payloads; only the host owns the Agent ModelContext lifecycle.

This separation is the main Host Integration PoC: **the same Drama Plugin core can be consumed by different agent hosts without moving the agent loop into the plugin.**

## Configuration

`DramaPlugin.load()` defaults to coherent Mock providers and needs no network.

Copy `config/drama-plugin.example.yaml` to define another configuration and pass it as `config_path`.

Each domain can be selected independently under `providers.<domain>.mode`.

Project, asset, history, generation, and media providers support:

```text
mock
http
```

Context supports:

```text
local
http
```

Only a domain selected as HTTP needs its corresponding `services.<domain>.base_url` and operation paths. The adapter assumes no URL layout.

Environment overrides use names such as:

```text
DRAMA_PLUGIN_PROVIDER_PROJECT_MODE
DRAMA_PLUGIN_PROVIDER_CONTEXT_MODE
DRAMA_PLUGIN_SERVICE_PROJECT_BASE_URL
DRAMA_PLUGIN_SERVICE_PROJECT_API_TOKEN
```

Never commit tokens. Environment values override YAML.

Mixed compositions are supported, for example:

- HTTP project data + Mock assets + local context projection;
- remote HTTP context service + Mock providers for every other domain.

## MCP and agent hosts

A future MCP adapter should implement the same provider protocols and register the same tool codes. Skills remain unchanged.

A Java context service can replace `LocalContextProvider` with `RemoteContextProvider` while returning the identical `DramaModelContext` and `DramaContextPatch` contracts through:

```text
build_context
refresh_context
```

This allows service implementations to evolve independently from the plugin's domain contracts.

## Security model

Drama Plugin sits on security-sensitive boundaries between model-generated decisions and external capabilities. The project therefore favors explicit, inspectable integration points.

Important surfaces include:

- untrusted model or user inputs entering tool calls;
- tool input/output schema validation;
- permissions and capability exposure;
- untrusted responses from HTTP or future MCP services;
- dependency and provider configuration;
- secrets passed through environment-backed configuration;
- context returned to the host model runtime.

The plugin should not silently expand its own authority. Tool execution and model-runtime decisions remain visible to, and controlled by, the host.

## Scope

Drama Plugin is an integration layer, not a complete drama platform.

It intentionally leaves these concerns outside the core:

- agent-loop implementation;
- database persistence;
- RAG infrastructure;
- asset storage and management;
- image/video generation engines;
- media processing;
- host-specific model lifecycle management.

Keeping these concerns external lets the plugin stay small, testable, and reusable.

## Current direction

The current implementation focuses on:

- stable domain contracts;
- Skill and tool discovery;
- Mock/HTTP provider composition;
- local or remote context projection;
- host integration;
- future MCP compatibility.

The next integrations should preserve these contracts rather than grow a second agent runtime inside the plugin.

## Documentation

See [`docs/architecture.md`](docs/architecture.md) for architectural boundaries and design decisions.
