"""Immutable data model, validation issues and the error type of the library."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

ErrorCode = Literal["too_large", "yaml_syntax", "alias_forbidden", "structure", "view"]
IssueCode = Literal["unknown_ref", "duplicate_id", "wrong_parent", "external_with_children"]

QUOTE_LIMIT = 200
_ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


def is_valid_id(value: object) -> bool:
    """Return ``True`` if ``value`` is a Mermaid-safe id (``^[A-Za-z][A-Za-z0-9_]*$``).

    The whole string must match, so a trailing newline is rejected.
    """
    return isinstance(value, str) and _ID_RE.fullmatch(value) is not None


def clip(value: str, limit: int = QUOTE_LIMIT) -> str:
    """Return ``value`` shortened to at most ``limit`` characters."""
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def quote(value: str) -> str:
    """Return a printable quotation of at most ``QUOTE_LIMIT`` characters of ``value``."""
    return repr(clip(value))


class C4Error(Exception):
    """Base error of the library.

    Attributes:
        code: Stable machine-readable error code.
        message: Human-readable message (quotes at most 200 characters of input).
        path: Location in the model, for example ``relations[3].target``; may be empty.
    """

    def __init__(self, code: ErrorCode, message: str, path: str = "") -> None:
        super().__init__(message)
        self.code: ErrorCode = code
        self.message = message
        self.path = path


@dataclass(frozen=True)
class Person:
    """A person (actor) that uses the systems."""

    id: str
    name: str
    description: str = ""


@dataclass(frozen=True)
class System:
    """A software system; ``external`` marks systems outside the modelled scope."""

    id: str
    name: str
    description: str = ""
    external: bool = False


@dataclass(frozen=True)
class Container:
    """A deployable unit inside the system whose id is ``system``."""

    id: str
    name: str
    description: str = ""
    system: str = ""
    technology: str = ""


@dataclass(frozen=True)
class Component:
    """A building block inside the container whose id is ``container``."""

    id: str
    name: str
    description: str = ""
    container: str = ""
    technology: str = ""


@dataclass(frozen=True)
class Relation:
    """A directed relation between two elements, identified by their ids."""

    source: str
    target: str
    label: str = ""
    technology: str | None = None


@dataclass(frozen=True)
class Model:
    """The whole architecture model; every collection keeps the input order."""

    people: tuple[Person, ...] = ()
    systems: tuple[System, ...] = ()
    containers: tuple[Container, ...] = ()
    components: tuple[Component, ...] = ()
    relations: tuple[Relation, ...] = ()


@dataclass(frozen=True)
class Issue:
    """A semantic problem found by :func:`c4_from_yaml.validate_model`."""

    path: str
    code: IssueCode
    message: str


Element = Person | System | Container | Component


def element_sections(model: Model) -> tuple[tuple[str, tuple[Element, ...]], ...]:
    """Return the element collections of ``model`` with their YAML section names."""
    return (
        ("people", model.people),
        ("systems", model.systems),
        ("containers", model.containers),
        ("components", model.components),
    )
