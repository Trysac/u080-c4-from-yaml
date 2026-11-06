"""Typed access to PyYAML.

PyYAML ships without inline types. Importing it dynamically keeps ``mypy --strict`` clean whether
or not third-party stubs are installed.
"""

from __future__ import annotations

import importlib
from typing import Any

yaml: Any = importlib.import_module("yaml")
