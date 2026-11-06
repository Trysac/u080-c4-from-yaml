"""Command line interface: ``python -m c4_from_yaml FILE --view context|container|component``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import cast

from .loader import DEFAULT_MAX_BYTES, load_model
from .model import C4Error
from .render import VIEWS, View, render
from .validate import validate_model

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="c4-from-yaml",
        description="Render C4 diagrams in Mermaid syntax from a YAML architecture model.",
    )
    parser.add_argument("file", metavar="FILE", help="YAML model file")
    parser.add_argument("--view", choices=VIEWS, help="diagram level to render")
    parser.add_argument(
        "--focus", help="system id (container view) or container id (component view)"
    )
    parser.add_argument("--out", help="write the diagram to this file instead of stdout")
    parser.add_argument(
        "--check",
        action="store_true",
        help="only validate the model (and the view, if given); print no diagram",
    )
    return parser


def _err(message: str) -> None:
    sys.stderr.write(message + "\n")


def _describe(error: C4Error) -> str:
    location = f" ({error.path})" if error.path else ""
    return f"error[{error.code}]: {error.message}{location}"


def _read(path: str) -> str:
    with Path(path).open("rb") as handle:
        data = handle.read(DEFAULT_MAX_BYTES + 1)
    return data.decode("utf-8-sig")


def main(argv: list[str] | None = None) -> int:
    """Run the command line interface and return the process exit code.

    Exit codes: 0 success, 1 validation findings or a view failure, 2 usage, IO or parse error.
    """
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else EXIT_ERROR
    view = cast("View | None", args.view)
    focus: str | None = args.focus
    check = bool(args.check)
    if view is None and not check:
        _err("error: --view is required unless --check is used")
        return EXIT_ERROR
    if view in ("container", "component") and focus is None:
        _err(f"error: --view {view} requires --focus")
        return EXIT_ERROR
    try:
        text = _read(args.file)
    except (OSError, UnicodeDecodeError) as exc:
        _err(f"error: cannot read input file ({type(exc).__name__})")
        return EXIT_ERROR
    try:
        model = load_model(text)
    except C4Error as exc:
        _err(_describe(exc))
        return EXIT_ERROR
    issues = validate_model(model)
    if issues:
        for issue in issues:
            _err(f"{issue.path}: {issue.code}: {issue.message}")
        return EXIT_FINDINGS
    output = ""
    if view is not None:
        try:
            output = render(model, view, focus=focus)
        except C4Error as exc:
            _err(_describe(exc))
            return EXIT_FINDINGS
    if check:
        return EXIT_OK
    if args.out is None:
        sys.stdout.write(output)
        return EXIT_OK
    try:
        Path(args.out).write_text(output, encoding="utf-8", newline="\n")
    except OSError as exc:
        _err(f"error: cannot write output file ({type(exc).__name__})")
        return EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
