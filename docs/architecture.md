# Drama Plugin architecture

## Boundary

Drama Plugin is a host-agnostic domain plugin. It exposes Skills, model-context contracts,
domain tools, provider abstractions, and a small loading runtime. It does not own an agent loop,
runtime/session context, databases, generation workflows, or remote-service lifecycle.

```text
Agent Host
  -> SkillRegistry / ToolRegistry / ContextBuilder
  -> stable drama domain contracts
  -> Project | Asset | History | Generation | Media | Context providers
  -> Mock, HTTP, or future MCP adapters
  -> external services
```

The dependency direction is always inward toward contracts. Skills name tool codes but never
construct providers. Tools delegate to providers and contain no business implementation.

## Modules

- `contracts`: small Pydantic v2 domain models. No persistence or transport fields leak in.
- `skills`: loads `skill.yaml` plus the human/agent-facing `SKILL.md`; it does not execute SOPs.
- `tools`: registers stable input/output JSON Schema, descriptions, and injected async provider
  callables by tool code. Schemas come from declared domain contracts, not provider reflection.
- `providers.base`: async domain protocols.
- `providers.mock`: coherent offline demo services.
- `providers.http`: configurable transport adapter; every operation path comes from config.
- `context`: the `Drama Domain -> Model Context` projection layer. Local and remote context
  providers return the same `DramaModelContext` contract.
- `plugin.py`: composition root that loads configuration/manifests, providers, skills, and tools.

## Context design

`RuntimeContext` belongs to the host and is intentionally absent. `DramaModelContext` contains
only project/story/episode/scene/shot, entities, resolved assets, evidence, generation state, and
constraints. `ContextBuildRequest` selects a scope and extensible purpose. Scope handlers and
purpose projections use registries, avoiding a growing purpose-driven conditional.

`build()` returns a versioned full context. Cross-boundary Context JSON uses Pydantic aliases as its
canonical representation. `refresh()` rebuilds the projection and emits a simple
top-level `DramaContextPatch` containing `base_version`, `new_version`, and typed changes. The host
decides if and how to merge that payload into an LLM context.

## Provider and transport decisions

Each domain provider is selected independently in configuration. The local context provider composes domain providers, which may themselves be Mock or HTTP. A remote context provider can later consume
a Java context service through `build_context` and `refresh_context`, without changing callers or
contracts. HTTP endpoints are operation mappings in configuration; URL paths are never assumed.
MCP remains a future adapter beside Mock and HTTP rather than a dependency of domain interfaces.

## Manifest strategy

`plugin.yaml` is the stable Drama manifest. `.codex-plugin/plugin.json` is a thin optional Codex
discovery adapter and is not consumed by the runtime. No marketplace, MCP SDK, Agent SDK, workflow
engine, database, or web server is introduced in phase one.
