# c4-from-yaml

[![PyPI version](https://img.shields.io/pypi/v/trysac-c4-from-yaml)](https://pypi.org/project/trysac-c4-from-yaml/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-c4-from-yaml)](LICENSE)
[![CI](https://github.com/Trysac/u080-c4-from-yaml/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u080-c4-from-yaml/actions/workflows/ci.yml)

Generate C4 context, container and component diagrams in Mermaid syntax from one validated YAML architecture model with safe loading

## Problem

Architecture diagrams drawn by hand go stale because each view is edited separately. Structurizr
solves this with its own DSL and a Java toolchain, which is heavy for small teams. A YAML model
rendered to Mermaid C4 keeps one source of truth that GitHub and documentation sites render natively.

## Install

```sh
pip install trysac-c4-from-yaml
# or
uv add trysac-c4-from-yaml
```

Requires Python 3.10 or newer. Depends on pyyaml>=6,<7.

## Usage

```python
from c4_from_yaml import load_model, render, validate_model

text = """\
people:
  - {id: u, name: User, description: Buys}
systems:
  - {id: shop, name: Shop, description: Sells}
relations:
  - {source: u, target: shop, label: Uses}
"""
model = load_model(text)
assert validate_model(model) == []
print(render(model, "context"))
# C4Context
#     Person(u, "User", "Buys")
#     System(shop, "Shop", "Sells")
#     Rel(u, shop, "Uses")
```

### CLI

```sh
c4-from-yaml FILE --view context|container|component [--focus ID] [--out FILE] [--check]
```

The `container` view needs `--focus` with a system id; `component` needs a container id.

Exit codes: `0` success, `1` validation issues found, `2` usage, IO or YAML error
(missing file, bad YAML, `--view container` without `--focus`).

### Errors

`load_model` and `render` raise `C4Error` with a `code` and `path`:
`too_large`, `yaml_syntax`, `alias_forbidden` (anchors and aliases are rejected),
`structure` and `view`. `validate_model` returns `Issue` objects with code
`unknown_ref`, `duplicate_id`, `wrong_parent` or `external_with_children`.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
