"""Shared Python import-path bootstrap for repository tooling.

Execution entry points that are launched directly from the repository root need
the project root and `src` directory to be importable.
"""

from __future__ import annotations

from pathlib import Path
import sys


def ensure_min_python(min_version: tuple[int, int] = (3, 11), *, script_name: str | None = None) -> None:
    """Reject unsupported Python runtimes early with clear operational guidance."""
    if sys.version_info < (min_version[0], min_version[1]):
        script_label = script_name or Path(sys.argv[0]).name
        raise SystemExit(
            "error: unsupported Python runtime for PQTS tooling; "
            f"{script_label} requires Python>={min_version[0]}.{min_version[1]} and was invoked with "
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )


def ensure_repo_python_path() -> None:
    repo_root = Path(__file__).resolve().parent
    src_root = repo_root / "src"
    additions = [str(repo_root)]
    if src_root.exists():
        additions.append(str(src_root))
    additions = [entry for entry in additions if entry not in sys.path]
    if additions:
        sys.path = [*additions, *sys.path]
