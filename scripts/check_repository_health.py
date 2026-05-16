#!/usr/bin/env python3
"""Repository health checks that avoid project-specific dependencies."""

from __future__ import annotations

import csv
import json
import os
import py_compile
import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".mypy_cache", ".next", ".pytest_cache", ".ruff_cache", ".venv", "build", "dist", "node_modules", "site-packages", "target"}
MANIFEST_NAMES = {
    "Cargo.toml",
    "Makefile",
    "mkdocs.yml",
    "package.json",
    "pom.xml",
    "pnpm-workspace.yaml",
    "pyproject.toml",
    "setup.py",
    "status.csv",
    "submission-metadata.json",
}
MANIFEST_SUFFIXES = (".sln", ".slnx")


def fail(message: str) -> NoReturn:
    """Exit with a health-check failure message."""
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def require_nonempty(*names: str) -> Path:
    """Return the first named non-empty file, or fail."""
    for name in names:
        candidate = ROOT / name
        if candidate.is_file() and candidate.stat().st_size > 0:
            print(f"ok: {name}")
            return candidate
    fail("missing non-empty file: " + " or ".join(names))


def find_manifests() -> list[Path]:
    """Find project manifests while skipping dependency and build folders."""
    manifests: list[Path] = []
    for current, dirs, files in os.walk(ROOT):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        current_path = Path(current)
        for filename in files:
            path = current_path / filename
            if (filename in MANIFEST_NAMES or path.suffix in MANIFEST_SUFFIXES) and path.stat().st_size > 0:
                manifests.append(path)
    return sorted(manifests, key=lambda path: str(path.relative_to(ROOT)))


def check_json(path: Path) -> None:
    """Validate that a file contains a JSON object."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path.relative_to(ROOT)} is invalid JSON: {exc}")
    if not isinstance(data, dict):
        fail(f"{path.relative_to(ROOT)} must contain a JSON object")
    print(f"ok: parsed {path.relative_to(ROOT)}")


def check_csv(path: Path) -> None:
    """Validate that a CSV file has at least a header row."""
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    if not rows or not rows[0]:
        fail(f"{path.relative_to(ROOT)} must include a header row")
    print(f"ok: parsed {path.relative_to(ROOT)}")


def check_python(path: Path) -> None:
    """Validate that a Python file compiles."""
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError as exc:
        fail(f"{path.relative_to(ROOT)} does not compile: {exc.msg}")
    print(f"ok: compiled {path.relative_to(ROOT)}")


def main() -> None:
    """Run repository health checks."""
    require_nonempty("README.md", "README.rst")
    require_nonempty(".gitignore")

    workflows_dir = ROOT / ".github" / "workflows"
    if not workflows_dir.is_dir() or not any(workflows_dir.glob("*.y*ml")):
        fail("missing GitHub Actions workflow")
    print("ok: GitHub Actions workflow present")

    manifests = find_manifests()
    if not manifests:
        fail("missing recognizable project manifest or publication metadata")
    display = ", ".join(str(path.relative_to(ROOT)) for path in manifests[:8])
    if len(manifests) > 8:
        display += f", ... +{len(manifests) - 8} more"
    print("ok: manifest coverage -> " + display)

    for name in ("package.json", "submission-metadata.json"):
        path = ROOT / name
        if path.exists():
            check_json(path)

    status_csv = ROOT / "status.csv"
    if status_csv.exists():
        check_csv(status_csv)

    for name in ("render_preprint_pdf.py", "docs/conf.py"):
        path = ROOT / name
        if path.exists():
            check_python(path)

    if (ROOT / "paper.md").exists():
        require_nonempty("abstract.txt")
        require_nonempty("keywords.txt")

    print("repository health checks passed")


if __name__ == "__main__":
    main()
