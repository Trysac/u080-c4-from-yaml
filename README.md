# c4-from-yaml

[![PyPI version](https://img.shields.io/pypi/v/trysac-c4-from-yaml)](https://pypi.org/project/trysac-c4-from-yaml/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-c4-from-yaml)](LICENSE)
[![CI](https://github.com/Trysac/u080-c4-from-yaml/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u080-c4-from-yaml/actions/workflows/ci.yml)

Generate C4 context, container and component diagrams in Mermaid syntax from one validated YAML architecture model with safe loading

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-c4-from-yaml
# or
uv add trysac-c4-from-yaml
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import c4_from_yaml

# normalize() trims surrounding whitespace and lower-cases the text.
print(c4_from_yaml.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    c4_from_yaml.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
