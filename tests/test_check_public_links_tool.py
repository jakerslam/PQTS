from __future__ import annotations

from pathlib import Path

from tools.check_public_links import dedupe_urls, evaluate_urls, load_project_urls, load_required_urls


def test_load_project_urls_reads_project_url_values(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "pqts"
version = "0.1.0"

[project.urls]
Homepage = "https://example.com/home"
Documentation = "https://example.com/docs"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    urls = load_project_urls(pyproject)
    assert urls == ["https://example.com/home", "https://example.com/docs"]


def test_load_required_urls_ignores_comments_and_blank_lines(tmp_path: Path) -> None:
    listing = tmp_path / "required.txt"
    listing.write_text(
        """
# comment
https://example.com/a

https://example.com/b
""".strip()
        + "\n",
        encoding="utf-8",
    )

    assert load_required_urls(listing) == ["https://example.com/a", "https://example.com/b"]


def test_dedupe_urls_preserves_order() -> None:
    assert dedupe_urls(
        [
            "https://example.com/a",
            "https://example.com/b",
            "https://example.com/a",
            "",
            " https://example.com/c ",
        ]
    ) == [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
    ]


def test_evaluate_urls_uses_checker_results() -> None:
    outcomes = {
        "https://ok.example": (True, 200, "ok"),
        "https://bad.example": (False, 404, "http_404"),
    }

    def checker(url: str, timeout: float) -> tuple[bool, int, str]:
        assert timeout == 5.0
        return outcomes[url]

    passes, failures = evaluate_urls(
        ["https://ok.example", "https://bad.example"],
        timeout=5.0,
        checker=checker,
    )

    assert passes == [("https://ok.example", 200, "ok")]
    assert failures == [("https://bad.example", 404, "http_404")]
