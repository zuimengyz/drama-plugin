---
name: historical-research
description: Build a traceable historical research context for drama creation. Use when an agent must investigate people, events, places, disputed claims, uncertainty, or the defensible boundary between evidence and dramatic invention.
---

# Historical Research

Frame a focused question and retain source identity with each material claim. Distinguish documented fact, supported inference, unresolved dispute, and dramatic invention. Prefer primary evidence when available and never turn a plausible inference into certain history.

Use supplied evidence before searching. Use `research.search_sources` when source discovery is needed. Use `research.search_events`, `research.search_people`, or `research.search_locations` only when the unresolved question concerns that category. Use `research.verify_claim` when a consequential claim must be assessed against available evidence. Do not search merely to repeat adequate supplied evidence.

Keep findings in Agent Run Context by default; do not create drama entities or a historical-source persistence domain. Complete when consequential claims are supported or explicitly uncertain and the permitted dramatic latitude is clear.
