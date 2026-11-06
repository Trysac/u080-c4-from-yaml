# Usage

`c4_from_yaml` renders one YAML architecture model as Mermaid C4 diagrams.

## Model format

Top-level keys: `people`, `systems`, `containers`, `components`, `relations`. Unknown keys or wrong
types raise `C4Error` with code `structure` and the path of the offending entry.

| Section | Fields |
|---|---|
| `people` | `id`, `name`, `description` |
| `systems` | `id`, `name`, `description`, `external` (boolean) |
| `containers` | `id`, `name`, `description`, `system`, `technology` |
| `components` | `id`, `name`, `description`, `container`, `technology` |
| `relations` | `source`, `target`, `label`, `technology` |

Ids match `^[A-Za-z][A-Za-z0-9_]*$` so that they are safe as Mermaid aliases and are unique across all
element kinds. `id` and `name` are required; the other element fields default to an empty string.

## Safe loading

`load_model` checks the size in UTF-8 bytes, scans the YAML event stream (anchors and aliases are
rejected, which blocks alias expansion and `<<` merges; depth is limited), and only then calls
`yaml.safe_load`. Limits: `max_bytes` (1 MiB), `max_depth` (20), `max_elements` (2000, counting
people, systems, containers and components).

## Views

- `context`: people and systems.
- `container`: needs `focus` as a system id; shows its containers in a `System_Boundary` plus the
  directly connected people and systems.
- `component`: needs `focus` as a container id; shows its components in a `Container_Boundary` plus
  directly connected elements.

Relations whose endpoints are hidden are lifted to the nearest visible ancestor. Lifted
self-relations are dropped, duplicates keep the first label, and a relation that ends at the focused
system or container itself is dropped because Mermaid cannot attach a relation to a boundary.
Labels are escaped (`"` becomes `'`, runs of CR, LF and tab become one space); HTML in labels is not
defended, so rely on the page's Mermaid `securityLevel`.

## Command line

```
python -m c4_from_yaml FILE --view context|container|component [--focus ID] [--out FILE] [--check]
```

Exit codes: 0 success, 1 validation findings or a view failure, 2 usage, IO or parse error.
