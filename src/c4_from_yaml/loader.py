"""Safe loading of a YAML architecture model into an immutable :class:`Model`."""

from __future__ import annotations

import logging
from typing import Any

from ._yaml import yaml
from .model import (
    C4Error,
    Component,
    Container,
    Model,
    Person,
    Relation,
    System,
    clip,
    is_valid_id,
    quote,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

DEFAULT_MAX_BYTES = 1_048_576
DEFAULT_MAX_DEPTH = 20
DEFAULT_MAX_ELEMENTS = 2000

_SECTIONS = ("people", "systems", "containers", "components", "relations")
_ELEMENT_SECTIONS = _SECTIONS[:4]


def load_model(
    text: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_elements: int = DEFAULT_MAX_ELEMENTS,
) -> Model:
    """Parse and structurally validate a YAML architecture model.

    The text is size-checked in UTF-8 bytes, scanned as a YAML event stream (anchors and aliases are
    rejected, nesting depth is limited) and only then loaded with ``yaml.safe_load``.

    Args:
        text: The YAML document.
        max_bytes: Maximum size of ``text`` in UTF-8 bytes.
        max_depth: Maximum nesting depth of mappings and sequences (the root counts as 1).
        max_elements: Maximum number of people, systems, containers and components together.

    Raises:
        C4Error: ``too_large``, ``yaml_syntax``, ``alias_forbidden`` or ``structure``.
    """
    if not isinstance(text, str):
        raise C4Error("structure", "input must be text")
    _check_size(text, max_bytes)
    _scan_events(text, max_depth)
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise _syntax_error(exc) from exc
    except RecursionError as exc:
        raise C4Error("too_large", "document is nested too deeply") from exc
    model = _build(data, max_elements)
    logger.debug(
        "loaded model: %d elements, %d relations",
        len(model.people) + len(model.systems) + len(model.containers) + len(model.components),
        len(model.relations),
    )
    return model


def _check_size(text: str, max_bytes: int) -> None:
    # A string with more characters than max_bytes has at least that many UTF-8 bytes, so the
    # encoded copy is only made for inputs that are already small.
    if len(text) > max_bytes or len(text.encode("utf-8", errors="surrogatepass")) > max_bytes:
        raise C4Error("too_large", f"input exceeds {max_bytes} bytes")


def _syntax_error(exc: Exception) -> C4Error:
    problem = getattr(exc, "problem", None) or getattr(exc, "reason", None) or "invalid YAML"
    mark = getattr(exc, "problem_mark", None)
    where = ""
    if mark is not None:
        where = f" at line {mark.line + 1}, column {mark.column + 1}"
    detail = clip(str(problem).replace("\n", " "))
    return C4Error("yaml_syntax", f"invalid YAML{where}: {detail}")


def _scan_events(text: str, max_depth: int) -> None:
    depth = 0
    try:
        for event in yaml.parse(text, Loader=yaml.SafeLoader):
            if isinstance(event, yaml.AliasEvent) or getattr(event, "anchor", None) is not None:
                raise C4Error("alias_forbidden", "anchors and aliases are not allowed")
            if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
                depth += 1
                if depth > max_depth:
                    raise C4Error("too_large", f"nesting is deeper than {max_depth} levels")
            elif isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
                depth -= 1
    except yaml.YAMLError as exc:
        raise _syntax_error(exc) from exc


def _build(data: object, max_elements: int) -> Model:
    if data is None:
        return Model()
    if not isinstance(data, dict):
        raise C4Error("structure", "top level must be a mapping")
    for key in data:
        if key not in _SECTIONS:
            raise C4Error("structure", f"unknown key {quote(str(key))}", clip(str(key)))
    lists: dict[str, list[Any]] = {}
    for name in _SECTIONS:
        raw = data.get(name)
        if raw is None:
            lists[name] = []
        elif isinstance(raw, list):
            lists[name] = raw
        else:
            raise C4Error("structure", f"'{name}' must be a list", name)
    total = sum(len(lists[name]) for name in _ELEMENT_SECTIONS)
    if total > max_elements:
        raise C4Error("too_large", f"model has more than {max_elements} elements")
    return Model(
        people=tuple(_person(i, raw) for i, raw in enumerate(lists["people"])),
        systems=tuple(_system(i, raw) for i, raw in enumerate(lists["systems"])),
        containers=tuple(_container(i, raw) for i, raw in enumerate(lists["containers"])),
        components=tuple(_component(i, raw) for i, raw in enumerate(lists["components"])),
        relations=tuple(_relation(i, raw) for i, raw in enumerate(lists["relations"])),
    )


def _mapping(item: object, path: str, allowed: frozenset[str]) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise C4Error("structure", "entry must be a mapping", path)
    for key in item:
        if key not in allowed:
            raise C4Error(
                "structure",
                f"unknown field {quote(str(key))}",
                f"{path}.{clip(str(key))}",
            )
    result: dict[str, Any] = item
    return result


def _opt(entry: dict[str, Any], key: str, path: str) -> str | None:
    value = entry.get(key)
    if value is not None and not isinstance(value, str):
        raise C4Error("structure", f"'{key}' must be a string", f"{path}.{key}")
    return value


def _req(entry: dict[str, Any], key: str, path: str, *, ident: bool = False) -> str:
    value = _opt(entry, key, path)
    if value is None:
        raise C4Error("structure", f"missing required field '{key}'", f"{path}.{key}")
    if ident and not is_valid_id(value):
        raise C4Error(
            "structure",
            f"'{key}' must match [A-Za-z][A-Za-z0-9_]*, got {quote(value)}",
            f"{path}.{key}",
        )
    return value


def _flag(entry: dict[str, Any], key: str, path: str) -> bool:
    value = entry.get(key)
    if value is None:
        return False
    if not isinstance(value, bool):
        raise C4Error("structure", f"'{key}' must be true or false", f"{path}.{key}")
    return value


def _person(index: int, raw: object) -> Person:
    path = f"people[{index}]"
    entry = _mapping(raw, path, frozenset({"id", "name", "description"}))
    return Person(
        id=_req(entry, "id", path, ident=True),
        name=_req(entry, "name", path),
        description=_opt(entry, "description", path) or "",
    )


def _system(index: int, raw: object) -> System:
    path = f"systems[{index}]"
    entry = _mapping(raw, path, frozenset({"id", "name", "description", "external"}))
    return System(
        id=_req(entry, "id", path, ident=True),
        name=_req(entry, "name", path),
        description=_opt(entry, "description", path) or "",
        external=_flag(entry, "external", path),
    )


def _container(index: int, raw: object) -> Container:
    path = f"containers[{index}]"
    entry = _mapping(raw, path, frozenset({"id", "name", "description", "system", "technology"}))
    return Container(
        id=_req(entry, "id", path, ident=True),
        name=_req(entry, "name", path),
        description=_opt(entry, "description", path) or "",
        system=_req(entry, "system", path, ident=True),
        technology=_opt(entry, "technology", path) or "",
    )


def _component(index: int, raw: object) -> Component:
    path = f"components[{index}]"
    allowed = frozenset({"id", "name", "description", "container", "technology"})
    entry = _mapping(raw, path, allowed)
    return Component(
        id=_req(entry, "id", path, ident=True),
        name=_req(entry, "name", path),
        description=_opt(entry, "description", path) or "",
        container=_req(entry, "container", path, ident=True),
        technology=_opt(entry, "technology", path) or "",
    )


def _relation(index: int, raw: object) -> Relation:
    path = f"relations[{index}]"
    entry = _mapping(raw, path, frozenset({"source", "target", "label", "technology"}))
    return Relation(
        source=_req(entry, "source", path, ident=True),
        target=_req(entry, "target", path, ident=True),
        label=_opt(entry, "label", path) or "",
        technology=_opt(entry, "technology", path),
    )
