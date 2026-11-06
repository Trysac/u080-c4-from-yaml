# Load YAML through an event-stream scan and render Mermaid C4 views from one model

Status: accepted (generated, pending human review)

## Context

Hand-drawn architecture diagrams go stale because every view is edited separately. The model must be loaded from untrusted YAML, which has alias expansion (billion laughs), merge keys and arbitrary tags, and the output must be Mermaid C4 text that is safe to embed.

## Decision

Keep one frozen dataclass model. Load it by checking the UTF-8 size, scanning yaml.parse events (any anchor or alias is rejected, nesting depth is counted from collection start events), then calling yaml.safe_load only. Validate semantics in a separate pure function and have render() refuse invalid models. Ids are restricted to a Mermaid-safe alphabet and labels are escaped. Each view is defined by a representative function that lifts hidden endpoints to the nearest visible ancestor; relations that end at the focused boundary itself are dropped. PyYAML is imported dynamically so strict mypy needs no stubs.

## Consequences

Documents that use anchors or aliases are always rejected, even harmless ones. Parsing cost is bounded by max_bytes, max_depth and max_elements. Relations to the focused system or container are not drawn in the deeper views. The core depends only on PyYAML and stays portable to Pyodide. HTML in labels is not sanitised, so the host page's Mermaid securityLevel is the defence.
