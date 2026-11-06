"""Behavior tests for the public API of c4_from_yaml."""

from __future__ import annotations

import pytest

import c4_from_yaml


def test_normalize_trims_and_lowercases() -> None:
    assert c4_from_yaml.normalize("  Hello World ") == "hello world"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_normalize_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        c4_from_yaml.normalize(value)


def test_version_is_semver() -> None:
    parts = c4_from_yaml.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
