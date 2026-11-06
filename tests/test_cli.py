"""Tests for the command line interface."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

from c4_from_yaml.__main__ import main


def yml(*lines: str) -> str:
    return "\n".join(lines) + "\n"


GOOD = yml(
    "people:",
    "  - {id: u, name: User, description: Buys}",
    "systems:",
    "  - {id: shop, name: Shop, description: Sells}",
    "relations:",
    "  - {source: u, target: shop, label: Uses}",
)
EXPECTED = yml(
    "C4Context",
    '    Person(u, "User", "Buys")',
    '    System(shop, "Shop", "Sells")',
    '    Rel(u, shop, "Uses")',
)
BAD = GOOD + "  - {source: u, target: nope, label: X}\n"
CONTAINERS = yml(
    "systems:",
    "  - {id: shop, name: Shop}",
    "containers:",
    "  - {id: web, name: Web, system: shop}",
)


def write(tmp_path: Path, text: str) -> str:
    path = tmp_path / "model.yaml"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_success_prints_diagram(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([write(tmp_path, GOOD), "--view", "context"]) == 0
    assert capsys.readouterr().out == EXPECTED


def test_out_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "diagram.mmd"
    code = main([write(tmp_path, GOOD), "--view", "context", "--out", str(target)])
    assert code == 0
    assert target.read_text(encoding="utf-8") == EXPECTED
    assert capsys.readouterr().out == ""


def test_out_to_directory_is_an_io_error(tmp_path: Path) -> None:
    code = main([write(tmp_path, GOOD), "--view", "context", "--out", str(tmp_path)])
    assert code == 2


def test_issues_return_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([write(tmp_path, BAD), "--view", "context"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "relations[1].target" in captured.err
    assert "unknown_ref" in captured.err


def test_missing_file_returns_two(tmp_path: Path) -> None:
    assert main([str(tmp_path / "missing.yaml"), "--view", "context"]) == 2


def test_invalid_utf8_returns_two(tmp_path: Path) -> None:
    path = tmp_path / "model.yaml"
    path.write_bytes(b"\xff\xfe\x00")
    assert main([str(path), "--view", "context"]) == 2


def test_yaml_errors_return_two(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([write(tmp_path, "a: &x 1\nb: *x\n"), "--view", "context"]) == 2
    assert "alias_forbidden" in capsys.readouterr().err
    assert main([write(tmp_path, "a: ["), "--view", "context"]) == 2
    assert main([write(tmp_path, "bogus: 1\n"), "--view", "context"]) == 2


def test_container_view_without_focus_returns_two(tmp_path: Path) -> None:
    assert main([write(tmp_path, CONTAINERS), "--view", "container"]) == 2
    assert main([write(tmp_path, CONTAINERS), "--view", "component"]) == 2


def test_missing_view_returns_two(tmp_path: Path) -> None:
    assert main([write(tmp_path, GOOD)]) == 2


def test_invalid_view_choice_returns_two(tmp_path: Path) -> None:
    assert main([write(tmp_path, GOOD), "--view", "deployment"]) == 2


def test_help_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    assert "--view" in capsys.readouterr().out


def test_container_view_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main([write(tmp_path, CONTAINERS), "--view", "container", "--focus", "shop"])
    assert code == 0
    assert "System_Boundary(shop" in capsys.readouterr().out


def test_wrong_focus_returns_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main([write(tmp_path, CONTAINERS), "--view", "container", "--focus", "nope"])
    assert code == 1
    assert "error[view]" in capsys.readouterr().err


def test_context_ignores_focus(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([write(tmp_path, GOOD), "--view", "context", "--focus", "zzz"]) == 0
    assert capsys.readouterr().out == EXPECTED


def test_check_mode(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([write(tmp_path, GOOD), "--check"]) == 0
    assert capsys.readouterr().out == ""
    assert main([write(tmp_path, BAD), "--check"]) == 1
    assert main([write(tmp_path, GOOD), "--check", "--view", "context"]) == 0
    code = main([write(tmp_path, CONTAINERS), "--check", "--view", "container", "--focus", "x"])
    assert code == 1
    assert main([write(tmp_path, CONTAINERS), "--check", "--view", "container"]) == 2


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_module_entry_point(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["c4-from-yaml"])
    with pytest.raises(SystemExit) as info:
        runpy.run_module("c4_from_yaml.__main__", run_name="__main__")
    assert info.value.code == 2
