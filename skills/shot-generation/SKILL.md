---
name: shot-generation
description: Prepare and submit image or video generation for an approved historical-drama shot. Use when a shot needs a generation plan, effective visual references, compilation, submission, status checks, or result inspection.
---

# Shot Generation

Build SHOT context, confirm the requested `generationTarget`, and use resolved effective assets with semantic media metadata. Create a plan, compile it through the generation service, and submit only when inputs are sufficient.

Skip creation or compilation when state shows it is already complete. Retry or stop according to returned state. Never implement or interpret ComfyUI/provider workflows inside the skill; `workflowCode` remains an opaque generation-service contract.
