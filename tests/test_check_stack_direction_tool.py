from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import check_stack_direction


def test_check_stack_direction_tool_passes_repo_defaults(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["check_stack_direction.py"])
    assert check_stack_direction.main() == 0


def test_validate_stack_direction_rejects_streamlit_in_core_dependencies(tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        """
[project]
dependencies = [
  "dash==2.18.2",
  "fastapi==0.135.1",
  "pydantic==2.12.0",
  "streamlit==1.55.0",
]

[project.optional-dependencies]
analytics = ["duckdb==1.3.2", "polars==1.34.0", "pyarrow==22.0.0"]
legacy_ui = ["streamlit==1.55.0"]
native = ["maturin==1.8.7"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    compose_path = tmp_path / "docker-compose.yml"
    compose_path.write_text("services:\n  dashboard:\n    command: [\"python\", \"src/dashboard/start.py\"]\n", encoding="utf-8")
    web_package_path = tmp_path / "package.json"
    web_package_path.write_text(
        json.dumps(
            {
                "dependencies": {
                    "next": "15.0.3",
                    "react": "18.2.0",
                    "react-dom": "18.2.0",
                }
            }
        ),
        encoding="utf-8",
    )
    stack_policy_path = tmp_path / "stack_policy.json"
    stack_policy_path.write_text(
        json.dumps(
            {
                "primary_language": "python",
                "native_kernel_languages": ["rust"],
                "rewrite_policy": {
                    "allow_full_native_rewrite": False,
                    "native_only_for_hotpath": True,
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="streamlit must not be in project.dependencies"):
        check_stack_direction.validate_stack_direction(
            pyproject_path=pyproject_path,
            compose_path=compose_path,
            web_package_path=web_package_path,
            stack_policy_path=stack_policy_path,
        )
