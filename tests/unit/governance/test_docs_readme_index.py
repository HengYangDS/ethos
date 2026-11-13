"""A directory README is its index: one role and a navigation-sized length."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.registry.docs.health import docs_health_report
from tests.support.documentation import documentation_fixture

if TYPE_CHECKING:
    from pathlib import Path

_README = "docs/topic/README.md"


@pytest.mark.parametrize(
    ("role", "padding", "gap"),
    [
        ("index", 0, ""),
        ("policy", 0, "docs_readme_not_index"),
        ("index", 120, "docs_index_too_long"),
    ],
    ids=["short-index", "policy", "long-index"],
)
def test_a_directory_readme_is_a_bounded_index(
    tmp_path: Path, role: str, padding: int, gap: str
) -> None:
    """A routed index passes; another role or more than 100 nonblank lines is a gap."""
    topic = tmp_path / "docs/topic"
    topic.mkdir(parents=True)
    for name in ("first", "second"):
        (topic / f"{name}.md").write_text(
            documentation_fixture(f"ethos:{name}", "explanation", "canonical", name.title())
        )
    text = documentation_fixture("docs:topic", role, "canonical", "Topic")
    text += "\nStart with [First](first.md).\n" + "".join(f"\nLine {n}.\n" for n in range(padding))
    (topic / "README.md").write_text(text)
    count = sum(bool(line.strip()) for line in text.splitlines())
    expected = {
        "": [],
        "docs_readme_not_index": [f"docs_readme_not_index:{_README}"],
        "docs_index_too_long": [f"docs_index_too_long:{_README}:{count}>100"],
    }[gap]
    assert docs_health_report(tmp_path)["readme_disposition"] == expected
