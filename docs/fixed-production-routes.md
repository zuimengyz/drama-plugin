# Fixed production routes and model selection

New formal production admits exactly one route: `ark_seedream_seedance`.
`image2_vidu` and `image2_minimax_h3` remain disabled. Historical receipts remain
recoverable; this policy does not authorize a new call on an old disabled route.

The external orchestration environment can select a model inside the active
family, without supplying or duplicating credentials:

```sh
DRAMA_PLUGIN_ACTIVE_ROUTE=ark_seedream_seedance
DRAMA_PLUGIN_ROUTE_IMAGE_MODEL=Doubao-Seedream-5.0-lite
DRAMA_PLUGIN_ROUTE_VIDEO_MODEL=seedance-2-fast
```

| Image choice | Official model ID |
| --- | --- |
| Doubao-Seedream-5.0-lite (default) | doubao-seedream-5-0-260128 |
| Doubao-Seedream-5.0-pro | doubao-seedream-5-0-pro-260628 |
| Doubao-Seedream-5.0-flash | doubao-seedream-5-0-flash-260915 |

The Lite alias `doubao-seedream-5-0-lite-260128` normalizes to its primary ID.
Unknown models fail closed. Video options use the existing registry keys
`seedance-2-fast`, `seedance-2-standard`, `seedance-2-mini`; existing per-model
enabled flags still apply at live submission.

Seedream reuses `settings()['seedance']`: `DRAMA_VIDEO_SEEDANCE_API_KEY` and
`DRAMA_VIDEO_SEEDANCE_BASE_URL`. The base must be
`https://ark.cn-beijing.volces.com/api/v3`; image calls use `/images/generations`.
No key is written into a Work, request body, prompt, receipt or route record.

`config.production_routes.selected()` exposes the resolved choice/count.
Formal route save and begin-submission check the active video selection; formal
still begin-submission checks the selected image provider/model. Provider wire
unit tests can continue to exercise retained adapters independently of formal
route admission.

The official still path projects the existing FrameSpec/IR through the same image
serializer. It currently supports text-to-image bootstrap only; reference/edit
inputs fail closed rather than being dropped. A proportional raster increase
meets the endpoint minimum without changing composition. Different model
selection produces a different compiled request and requires normal replan and
reservation. No automatic retry or free route/model switch is implied.

Model availability and account authorization are separate from realized quality
and Seedance portrait eligibility. A missing-prompt probe does not generate an
image or prove end-to-end generation. Paid use still requires formal admission,
budget/reservation, an actual official receipt, original bytes, Media persistence,
QC and downstream provenance verification. Merely selecting an Ark model or
storing a credential-source name is not proof of a trusted portrait.

Official sources: [model list](https://docs.volcengine.com/docs/ark/model-list?lang=zh),
[image API](https://docs.volcengine.com/docs/ark/image-generation-api?lang=en),
[portrait rules](https://docs.volcengine.com/docs/ark/seedance-portrait-asset-guide?lang=zh).
