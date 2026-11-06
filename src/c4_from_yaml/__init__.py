"""Generate C4 diagrams in Mermaid syntax from one validated YAML architecture model."""

from __future__ import annotations

from .loader import load_model
from .model import (
    C4Error,
    Component,
    Container,
    Issue,
    Model,
    Person,
    Relation,
    System,
)
from .render import render
from .validate import validate_model

__all__ = [
    "C4Error",
    "Component",
    "Container",
    "Issue",
    "Model",
    "Person",
    "Relation",
    "System",
    "__version__",
    "load_model",
    "render",
    "validate_model",
]

__version__ = "0.1.0"
