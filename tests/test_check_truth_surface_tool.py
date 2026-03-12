from __future__ import annotations

import json
from pathlib import Path

from tools.check_truth_surface import evaluate_truth_surface


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_truth_surface_passes_repo_defaults() -> None:
    errors = evaluate_truth_surface(
        policy_path=Path("config/release/truth_surface_policy.json"),
        pyproject_path=Path("pyproject.toml"),
        readme_path=Path("README.md"),
        quickstart_path=Path("docs/QUICKSTART_5_MIN.md"),
        development_summary_path=Path("docs/DEVELOPMENT_SUMMARY.md"),
        dashboard_app_path=Path("src/dashboard/app.py"),
        dashboard_start_path=Path("src/dashboard/start.py"),
    )
    assert errors == []


def test_truth_surface_flags_unqualified_install_when_pypi_unavailable(tmp_path: Path) -> None:
    policy = {
        "canonical_release_version": "0.1.0",
        "maturity": "alpha",
        "distribution": {"pypi": {"available": False, "package": "pqts"}},
        "ui_surface": {
            "dashboard_port": 8501,
            "required_markers": [],
            "quickstart_required_markers": [],
            "forbid_external_codepen": False,
        },
    }
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    pyproject = tmp_path / "pyproject.toml"
    _write(pyproject, "[project]\nname='pqts'\nversion='0.1.0'\n")
    readme = tmp_path / "README.md"
    _write(readme, "pip install pqts\n")
    quickstart = tmp_path / "QUICKSTART.md"
    _write(quickstart, "")
    dev_summary = tmp_path / "DEVELOPMENT_SUMMARY.md"
    _write(dev_summary, "")
    dash_app = tmp_path / "app.py"
    _write(dash_app, 'if __name__ == "__main__":\n    app.run(port=8501, debug=False)\n')
    dash_start = tmp_path / "start.py"
    _write(dash_start, "app.run(port=8501, debug=False)\n")

    errors = evaluate_truth_surface(
        policy_path=policy_path,
        pyproject_path=pyproject,
        readme_path=readme,
        quickstart_path=quickstart,
        development_summary_path=dev_summary,
        dashboard_app_path=dash_app,
        dashboard_start_path=dash_start,
    )
    assert any("unqualified install commands" in item for item in errors)


def test_truth_surface_flags_missing_package_first_markers_when_pypi_available(tmp_path: Path) -> None:
    policy = {
        "canonical_release_version": "0.1.0",
        "maturity": "alpha",
        "distribution": {"pypi": {"available": True, "package": "pqts"}},
        "ui_surface": {
            "dashboard_port": 8501,
            "required_markers": [],
            "quickstart_required_markers": [],
            "quickstart_package_markers": ["pip install -U pqts", "pqts quickstart --execute"],
            "forbid_external_codepen": False,
        },
    }
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    pyproject = tmp_path / "pyproject.toml"
    _write(pyproject, "[project]\nname='pqts'\nversion='0.1.0'\n")
    readme = tmp_path / "README.md"
    _write(readme, "")
    quickstart = tmp_path / "QUICKSTART.md"
    _write(quickstart, "git clone https://github.com/jakerslam/pqts.git\n")
    dev_summary = tmp_path / "DEVELOPMENT_SUMMARY.md"
    _write(dev_summary, "")
    dash_app = tmp_path / "app.py"
    _write(dash_app, 'if __name__ == "__main__":\n    app.run(port=8501, debug=False)\n')
    dash_start = tmp_path / "start.py"
    _write(dash_start, "app.run(port=8501, debug=False)\n")

    errors = evaluate_truth_surface(
        policy_path=policy_path,
        pyproject_path=pyproject,
        readme_path=readme,
        quickstart_path=quickstart,
        development_summary_path=dev_summary,
        dashboard_app_path=dash_app,
        dashboard_start_path=dash_start,
    )
    assert any("missing required package-first marker" in item for item in errors)
