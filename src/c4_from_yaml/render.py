"""Rendering of a validated model as Mermaid C4 diagrams."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Literal

from .model import (
    C4Error,
    Component,
    Container,
    Model,
    Person,
    System,
    element_sections,
    is_valid_id,
    quote,
)
from .validate import validate_model

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

View = Literal["context", "container", "component"]
VIEWS: tuple[View, ...] = ("context", "container", "component")

Rep = Callable[[str], str | None]

_HEADERS = {"context": "C4Context", "container": "C4Container", "component": "C4Component"}
_KIND_BY_SECTION = {
    "people": "person",
    "systems": "system",
    "containers": "container",
    "components": "component",
}
_INDENT = "    "
_WHITESPACE_RUN = re.compile(r"[\r\n\t]+")


def render(
    model: Model,
    view: View,
    *,
    focus: str | None = None,
    title: str | None = None,
) -> str:
    """Render ``model`` as a Mermaid C4 diagram.

    Views follow the C4 levels. ``context`` shows people and systems (``focus`` is ignored).
    ``container`` needs ``focus`` as a system id and shows its containers plus the directly
    connected people and systems. ``component`` needs ``focus`` as a container id and shows its
    components plus directly connected elements. A relation whose endpoints are hidden is lifted
    to the nearest visible ancestor; lifted self-relations are dropped, duplicates keep the first
    label, and a relation that ends at the focused system or container itself is dropped.

    Raises:
        C4Error: ``view`` for an unknown view or a missing or wrong ``focus``; ``structure`` if the
            model is invalid (see :func:`c4_from_yaml.validate_model`) or has unsafe ids.
    """
    if view not in VIEWS:
        raise C4Error("view", f"unknown view {quote(str(view))}", "view")
    _require_valid(model)
    kinds: dict[str, str] = {}
    names: dict[str, str] = {}
    parents: dict[str, str] = {}
    for section, items in element_sections(model):
        for item in items:
            kinds[item.id] = _KIND_BY_SECTION[section]
            names[item.id] = item.name
    for container in model.containers:
        parents[container.id] = container.system
    for component in model.components:
        parents[component.id] = component.container
    rep, inside = _scope(view, focus, kinds, parents, model)
    visible = _visible(view, model, rep, inside)
    lines = [_HEADERS[view]]
    if title is not None:
        lines.append(f"{_INDENT}title {_clean(title)}")
    lines.extend(_outside_lines(model, visible - inside))
    if view != "context" and focus is not None:
        lines.extend(_boundary_lines(view, focus, model, inside, names))
    relation_lines = _relation_lines(model, rep, visible)
    lines.extend(relation_lines)
    logger.debug("rendered %s view with %d relations", view, len(relation_lines))
    return "\n".join(lines) + "\n"


def _clean(value: str) -> str:
    return _WHITESPACE_RUN.sub(" ", value.replace('"', "'"))


def _q(value: str) -> str:
    return f'"{_clean(value)}"'


def _require_valid(model: Model) -> None:
    issues = validate_model(model)
    if issues:
        first = issues[0]
        raise C4Error("structure", f"model is invalid: {first.code}: {first.message}", first.path)
    for section, items in element_sections(model):
        for index, item in enumerate(items):
            if not is_valid_id(item.id):
                raise C4Error("structure", f"unsafe id {quote(item.id)}", f"{section}[{index}].id")


def _scope(
    view: View,
    focus: str | None,
    kinds: dict[str, str],
    parents: dict[str, str],
    model: Model,
) -> tuple[Rep, frozenset[str]]:
    def top(eid: str) -> str:
        while eid in parents:
            eid = parents[eid]
        return eid

    if view == "context":
        return top, frozenset()
    if focus is None:
        raise C4Error("view", f"{view} view requires a focus id", "focus")
    if view == "container":
        if kinds.get(focus) != "system":
            raise C4Error("view", f"focus {quote(focus)} is not a system id", "focus")
        container_ids = frozenset(c.id for c in model.containers if c.system == focus)

        def rep_container(eid: str) -> str | None:
            if eid == focus:
                return None
            if top(eid) != focus:
                return top(eid)
            return eid if kinds[eid] == "container" else parents[eid]

        return rep_container, container_ids
    if kinds.get(focus) != "container":
        raise C4Error("view", f"focus {quote(focus)} is not a container id", "focus")
    system = parents[focus]
    component_ids = frozenset(c.id for c in model.components if c.container == focus)

    def rep_component(eid: str) -> str | None:
        if eid in (focus, system):
            return None
        if eid in component_ids:
            return eid
        root = top(eid)
        if root != system:
            return root
        return eid if kinds[eid] == "container" else parents[eid]

    return rep_component, component_ids


def _visible(view: View, model: Model, rep: Rep, inside: frozenset[str]) -> set[str]:
    if view == "context":
        return {p.id for p in model.people} | {s.id for s in model.systems}
    visible = set(inside)
    for relation in model.relations:
        source = rep(relation.source)
        target = rep(relation.target)
        if source is None or target is None:
            continue
        if source in inside and target not in inside:
            visible.add(target)
        elif target in inside and source not in inside:
            visible.add(source)
    return visible


def _person_line(person: Person, indent: str) -> str:
    return f"{indent}Person({person.id}, {_q(person.name)}, {_q(person.description)})"


def _system_line(system: System, indent: str) -> str:
    macro = "System_Ext" if system.external else "System"
    return f"{indent}{macro}({system.id}, {_q(system.name)}, {_q(system.description)})"


def _tech_line(macro: str, item: Container | Component, indent: str) -> str:
    head = f"{indent}{macro}({item.id}, {_q(item.name)}, "
    return head + f"{_q(item.technology)}, {_q(item.description)})"


def _outside_lines(model: Model, outside: set[str]) -> list[str]:
    lines: list[str] = []
    for person in model.people:
        if person.id in outside:
            lines.append(_person_line(person, _INDENT))
    for system in model.systems:
        if system.id in outside:
            lines.append(_system_line(system, _INDENT))
    for container in model.containers:
        if container.id in outside:
            lines.append(_tech_line("Container", container, _INDENT))
    for component in model.components:
        if component.id in outside:
            lines.append(_tech_line("Component", component, _INDENT))
    return lines


def _boundary_lines(
    view: View,
    focus: str,
    model: Model,
    inside: frozenset[str],
    names: dict[str, str],
) -> list[str]:
    lines: list[str]
    if view == "container":
        lines = [f"{_INDENT}System_Boundary({focus}, {_q(names[focus])}) {{"]
        for container in model.containers:
            if container.id in inside:
                lines.append(_tech_line("Container", container, _INDENT * 2))
    else:
        lines = [f"{_INDENT}Container_Boundary({focus}, {_q(names[focus])}) {{"]
        for component in model.components:
            if component.id in inside:
                lines.append(_tech_line("Component", component, _INDENT * 2))
    lines.append(f"{_INDENT}}}")
    return lines


def _relation_lines(model: Model, rep: Rep, visible: set[str]) -> list[str]:
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for relation in model.relations:
        source = rep(relation.source)
        target = rep(relation.target)
        if source is None or target is None or source == target:
            continue
        if source not in visible or target not in visible or (source, target) in seen:
            continue
        seen.add((source, target))
        text = f"{_INDENT}Rel({source}, {target}, {_q(relation.label)}"
        if relation.technology:
            text += f", {_q(relation.technology)}"
        lines.append(text + ")")
    return lines
