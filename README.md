# Drama Plugin

Drama Plugin is the host-agnostic Agent Plugin layer for a source-driven historical short-drama
platform. It provides domain Skills, Pydantic contracts, tool descriptions, provider abstractions,
and a `Drama Domain -> Model Context` projection API.

**Drama Plugin does not own the agent loop.** Codex, an OpenAI Agent, or another harness decides
when to call tools and how to merge returned context. The plugin also does not implement databases,
RAG, asset management, media processing, or image/video generation services.

## Concepts

- **Skill**: a flexible domain SOP with context needs, decision/tool guidance, and completion rules.
- **Tool**: a stable, discoverable external-capability contract with explicit input/output JSON Schema. It contains no service business logic.
- **Provider**: the Mock/HTTP/future MCP implementation behind a domain tool.
- **ContextBuilder**: projects domain contracts into `DramaModelContext`; it does not manage host runtime context.
- **DramaPlugin**: loads manifests/configuration and composes registries and providers; it runs no LLM loop.

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

## Configuration

`DramaPlugin.load()` defaults to coherent Mock providers and needs no network. Copy
`config/drama-plugin.example.yaml` to define another configuration and pass it as `config_path`.
Select each domain independently under `providers.<domain>.mode`. Project, asset, history,
generation, and media support `mock` or `http`; context supports `local` or `http`. Only a domain
selected as HTTP needs its corresponding `services.<domain>.base_url` and operation paths. The
adapter assumes no URL layout.

Environment overrides use names such as `DRAMA_PLUGIN_PROVIDER_PROJECT_MODE`,
`DRAMA_PLUGIN_PROVIDER_CONTEXT_MODE`,
`DRAMA_PLUGIN_SERVICE_PROJECT_BASE_URL`, and `DRAMA_PLUGIN_SERVICE_PROJECT_API_TOKEN`. Never commit
tokens. Environment values override YAML.

This supports mixed compositions such as HTTP project data with Mock assets and a local context
projection, or a remote HTTP context service while every other domain remains Mock.

## MCP and agent hosts

A future MCP adapter should implement the same provider protocols and register the same tool codes;
Skills remain unchanged. A Java context service can replace `LocalContextProvider` with
`RemoteContextProvider` while returning the identical `DramaModelContext` and `DramaContextPatch`
contracts through `build_context` and `refresh_context`.

Codex, OpenAI Agents SDK, or a custom harness can inspect `plugin.skills.list()`,
`plugin.tools.list()`, `plugin.tools.describe(code)`, and `plugin.capabilities()`, then call
`plugin.context.build(...)`. Host-specific
manifest or tool-schema adapters belong at the integration edge. External services build context
payloads; only the host owns the Agent ModelContext lifecycle.

See [architecture.md](docs/architecture.md) for boundaries and design decisions.
