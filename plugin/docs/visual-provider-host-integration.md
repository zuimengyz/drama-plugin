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

V2-05 qualification: the table proves available input primitives, not artistic
suitability. The three-input Object Swap template passes images from nodes 2, 3,
10 to image_1, image_2, image_3 and inherits output dimensions from node 2. A
character card in that slot can produce 3:2 output even when the prompt requests
16:9. Inspect the current graph before binding it. Use `compile_frame` and the
packaged `skills/shot-production/scripts/visual_preflight.py` gate described in
[first-pass production](../skills/shot-production/references/first-pass-production.md)
for new image calls. The Host submits only a reserved request and records the
result and review before requesting another. Single static, two-person,
person-plus-prop, complex-pose and establishing tasks require representative
qualification, including reference-state changes; do not route solely by count.

## Codex setup example

Host-level configuration stays outside Skill Core. A Codex Host can register and authenticate the external provider with its normal MCP management flow:

```text
codex mcp add comfy-cloud --url https://cloud.comfy.org/mcp
codex mcp login comfy-cloud
```

At runtime the Host should expose both the bundled Drama tools and the conditional visual provider tools to the Agent. Missing Comfy Cloud must not block Work, Script, Episode, Scene, Shot, research, planning, or context reads; it blocks only visual execution and must produce `VISUAL_PROVIDER_UNAVAILABLE` or `VISUAL_PROVIDER_CAPABILITY_MISSING`.

## Video selection adapter and source entry (V2-06)

The plugin manifest already discovers `./skills/`; the neutral registry loads each
`skill.yaml` + `SKILL.md`. `video-model-selection` includes both and interface metadata.
Use the repository plugin tree as the package; the Python wheel alone has never
carried the skill directory. Do not assume an installed Codex cache refreshed.

Before a paid call, explicitly read the source Skill and run the source
`skills/shot-production/scripts/visual_preflight.py`, which prepends this plugin's
`src` and registers `hosts.comfy_video.verify_execution` with the neutral gate.
Record resolved module paths and SHA-256 of Skill, frame_request, production,
video_selection, adapter and entry script, plus current template/schema evidence.
This does not require changing global marketplace or MCP configuration.

`search_templates`, `get_template`, `get_template_schema`, `get_node` supply current
capability evidence. `estimate_credits` must receive the exact overridden graph for
quotation only; never submit that reconstructed quotation graph. Execute the
reserved `run_template` request (map `name` to `template_id` if runtime schema asks).
Record `get_job_status`/`get_output` and billing in the same attempt. The runtime
schema remains authoritative. Price tools may omit costs and need live verification.

The narrow adapter inspects direct LoadImage -> Flux3ImageToVideoNode,
MinimaxHailuo03FirstLastFrameNode or MinimaxHailuo03ReferenceNode -> SaveVideo.
It checks every node/link, native output, exposed defaults, exact input roles and
physical byte/upload receipt binding. MiniMax H3 and H3 Max are separate variants;
Max/ContextIR/regeneration/switch/subgraphs currently fail closed. Extra output
SaveVideo copies of the same node are one generation. This adapter does not change
the V2-05 image graph inspector or authorize arbitrary reference combinations.

The current Flux 3 node supports timed images, but the inspected project template
exposes one first frame; its wider node capabilities do not expand the project
contract. The inspected MiniMax reference template exposes one reference; it does
not enforce the first frame. The MiniMax FLF template binds two independent images.
Candidate evidence and current prices live in run artifacts, not a fixed model list
in the core Skill. Use no more than the requested limited trial scope.

## Durable completion and recovery

`visual_preflight.py persist --state <same-state> --input <completion.json>` completes
an existing provider attempt through `hosts/visual_delivery.py`. Its input contains
`attempt_id`, the existing `mcp_config`, an allowed staging `source_path`, a
rebuildable `cache`, and the known `work_id` / `shot_id`. The frozen output hash and
job remain in the original state. No generator is imported by this path.

The shared `complete_retained_media` queries stable source identity before import,
verifies get/resolve/full downloaded bytes and physical decoding, then writes and
rereads the business binding. Candidate storage returns `CANDIDATE_SAVED`; content,
technical conformance and user adoption remain independent. A decodable paid output
with a dimension failure may be saved as a candidate without claiming conformance.
An uncertain import stops at persistence recovery; investigate the stable source
before re-entering. The service enforces identical scope, MIME, size and SHA-256
when sourceRef already exists.

`production.generate_image` and `production.generate_video` finish through the same
closure before returning a durable result. Role dubbing retains its output and
pending import metadata by request fingerprint; import/binding recovery never
resynthesizes that output. Native adoption uses `prepare_bound_media(adopted=True)`
from a formal Shot binding. Low-level `assemble_av` only reports `LOCAL_READY` or
`ASSEMBLED`, which is not formal delivery. Explicit derivative completion uses
`audio-production/scripts/assemble_delivery.py` / `assemble_av_delivery`; it also
resumes imported/staged output without repeating mux.

Bindings contain stable mediaId/sourceRef/hash and review/adoption semantics.
Temporary provider upload names, content URLs and paths are transport/cache data,
not business identities. Adapter configuration selects the existing MCP endpoint;
Java continues to own private object-storage access and credentials.
