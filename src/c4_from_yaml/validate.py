"""Semantic validation of a :class:`Model`."""

from __future__ import annotations

from .model import Issue, Model, clip, element_sections


def validate_model(model: Model) -> list[Issue]:
    """Return every semantic problem of ``model`` (an empty list means the model is valid).

    Checks: ids are unique across all element kinds (``duplicate_id``, one issue per repeated id),
    relation endpoints and parents exist (``unknown_ref``), parents have the right kind
    (``wrong_parent``) and external systems have no containers (``external_with_children``).
    """
    issues: list[Issue] = []
    kinds = _check_ids(model, issues)
    for index, container in enumerate(model.containers):
        path = f"containers[{index}].system"
        _check_parent(issues, kinds, path, container.system, "systems")
    for index, component in enumerate(model.components):
        path = f"components[{index}].container"
        _check_parent(issues, kinds, path, component.container, "containers")
    parents = {container.system for container in model.containers}
    for index, system in enumerate(model.systems):
        if system.external and system.id in parents:
            message = f"external system '{clip(system.id)}' must not contain containers"
            issues.append(Issue(f"systems[{index}].external", "external_with_children", message))
    for index, relation in enumerate(model.relations):
        for end, ref in (("source", relation.source), ("target", relation.target)):
            if ref not in kinds:
                message = f"unknown reference '{clip(ref)}'"
                issues.append(Issue(f"relations[{index}].{end}", "unknown_ref", message))
    return issues


def _check_ids(model: Model, issues: list[Issue]) -> dict[str, str]:
    kinds: dict[str, str] = {}
    repeated: set[str] = set()
    for section, items in element_sections(model):
        for index, item in enumerate(items):
            if item.id not in kinds:
                kinds[item.id] = section
            elif item.id not in repeated:
                repeated.add(item.id)
                message = f"id '{clip(item.id)}' is defined more than once"
                issues.append(Issue(f"{section}[{index}].id", "duplicate_id", message))
    return kinds


def _check_parent(
    issues: list[Issue],
    kinds: dict[str, str],
    path: str,
    ref: str,
    expected: str,
) -> None:
    kind = kinds.get(ref)
    if kind is None:
        issues.append(Issue(path, "unknown_ref", f"unknown reference '{clip(ref)}'"))
    elif kind != expected:
        message = f"'{clip(ref)}' is defined in {kind}, expected {expected}"
        issues.append(Issue(path, "wrong_parent", message))
