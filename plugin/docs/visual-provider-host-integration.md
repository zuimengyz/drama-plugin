# Visual Provider Host integration

Drama Plugin bundles only its own `drama-tools` MCP server through `.mcp.json`. A visual provider is a conditional external Host dependency for image or video execution, not a Drama MCP, Domain, Java, Media, or Asset contract.

The `shot-production` Skill Core declares provider-neutral capabilities. Its OpenAI/Codex adapter currently identifies Comfy Cloud as the verified implementation:

```text
comfy-cloud
https://cloud.comfy.org/mcp
authentication: OAuth, managed by the Host
```

The Plugin does not store OAuth tokens, API keys, signed URLs, or provider login state. Codex is one supported Host; another Host may provide the same capabilities through its own MCP client or tool adapter.

## Current capability mapping

| Skill capability | Current Comfy Cloud tool |
| --- | --- |
| `visual.template.discover` | `search_templates`, `get_template`, and only when necessary `get_template_schema` |
| `visual.input.upload` | `upload_file` |
| `visual.image.generate` | `run_template` |
| `visual.job.wait` | `wait_for_job`, and only when necessary `get_job_status` |
| `visual.output.fetch` | `get_output` |

This table maps names to semantics only. The runtime MCP server is the source of truth for every tool's executable input and output schema.

## Current verified image preferences

These are provider implementation preferences, not stable Drama business contracts:

| Reference count | Current verified official template |
| --- | --- |
| 0 | `api_google_nano_banana2_text_to_image` |
| 1 | `image_mage_flow_edit_turbo_int8` |
| 2 | `image_qwen_image_edit_2511` |
| 3 | `api_bfl_flux2_max_sofa_swap` |

Use a preference directly when it is available and matches the generation intent. Search for a replacement official template only when it is unavailable or unsuitable. Never create a saved, custom, or dynamic workflow automatically.

## Codex setup example

Host-level configuration stays outside Skill Core. A Codex Host can register and authenticate the external provider with its normal MCP management flow:

```text
codex mcp add comfy-cloud --url https://cloud.comfy.org/mcp
codex mcp login comfy-cloud
```

At runtime the Host should expose both the bundled Drama tools and the conditional visual provider tools to the Agent. Missing Comfy Cloud must not block Work, Script, Episode, Scene, Shot, research, planning, or context reads; it blocks only visual execution and must produce `VISUAL_PROVIDER_UNAVAILABLE` or `VISUAL_PROVIDER_CAPABILITY_MISSING`.
