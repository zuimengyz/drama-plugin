# Drama Plugin architecture

## Boundary

Drama Plugin is a host-agnostic Skill Package. The Agent Host owns decisions and run lifecycle; Skills provide method, Tools perform actions, and external services retain facts or execute physical capabilities.

```text
Agent Host
  -> platform-neutral Skill Core
  -> stable Tool Contracts
  -> Mock, HTTP, MCP, or other host adapters
  -> Persistent Memory or physical production services
```

No Skill invokes another Skill. The Agent reads a result and chooses what happens next; the Work/Script/Episode/Scene/Shot hierarchy is not an execution pipeline.

## Persistent model

The System of Record owns only `Work`, `Script`, `Episode`, `Scene`, `Shot`, `Asset`, and `Media`. Parent IDs express the creative hierarchy directly. Historical evidence stays in Agent Research Context unless a future concrete requirement establishes a separate external research capability; it is not a Drama persistence domain.

Asset is stable reusable visual memory. Media is a stable handle to a physical image, video, or audio object. Asset selection is Agent reasoning. Media storage and Provider details stay behind adapters.

## Modules

- `contracts`: minimal Pydantic models with transport-neutral camelCase wire aliases.
- `skills`: discovers `SKILL.md` and `skill.yaml`; it never runs a fixed flow.
- `tools`: declares stable action semantics and JSON Schema; Tool handlers contain no creative decisions.
- `providers.base`: protocols for memory, assets, research, production, media, and context.
- `providers.mock`: coherent offline development facts and actions.
- `providers.http`: configurable transport adapter with no assumed endpoint layout.
- `context`: builds only the persistent-object chain and run fields needed by the current task.
- `plugin.py`: composition root without an Agent Loop or orchestrator.

## Context ownership

`DramaRunContext` may contain the current minimal persistent chain plus selected asset IDs, generated media IDs, Research Context, and temporary state. The Host owns insertion and merging. `DramaContextPatch` remains a small top-level refresh contract; it is not a state machine.

## Production boundary

`production.generate_image`, `production.generate_video`, and `production.generate_audio` accept business prompts and stable IDs. A ComfyUI or other Provider adapter may resolve Media storage, upload inputs, inject its private workflow, execute the Provider, persist output, and return a Media ID. None of those physical details belong in Skill Core or the stable Tool Contract.

## Codex adapter

`../.codex-plugin/plugin.json`, `.mcp.json`, and `agents/openai.yaml` are Codex/OpenAI discovery metadata. Platform-neutral business rules remain in `SKILL.md` and `skill.yaml`; another host can load the same Core and bind the same Tool codes without Codex.
