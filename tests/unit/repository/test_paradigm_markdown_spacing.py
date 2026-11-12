"""One blank-line rule for Markdown list items, decided from the CommonMark structure."""

from __future__ import annotations

import pytest
from markdown_it import MarkdownIt

from ethos.repository.paradigm.markdown_spacing import canonical_spacing
from ethos.repository.paradigm.markdown_spacing import spacing_violations

_REPAIRED = {
    "stray-blank": ("- one\n- two\n\n- three\n", "- one\n- two\n- three\n"),
    "two-paragraphs": (
        "- alpha\n- beta.\n\n  second.\n- gamma\n",
        "- alpha\n- beta.\n\n  second.\n\n- gamma\n",
    ),
    "introduced-list": ("- parent\n\n  - child\n- next\n", "- parent\n  - child\n- next\n"),
    "introduced-code": (
        "- run:\n\n  ```sh\n  x\n  ```\n\n- after\n",
        "- run:\n  ```sh\n  x\n  ```\n- after\n",
    ),
    "quoted": ("> - one\n>\n> - two\n", "> - one\n> - two\n"),
    "quoted-spread": (
        "> - a\n>\n>   second.\n> - b\n",
        "> - a\n>\n>   second.\n>\n> - b\n",
    ),
}
_CONFORMING = {
    "tight-nested": "- parent\n  - child one\n  - child two\n- next\n",
    "introduced-then-paragraph": "- intro:\n  - a\n  - b\n\n  Second paragraph.\n\n- next\n",
    "fenced-example": "Text.\n\n```md\n- a\n\n- b\n```\n",
}


@pytest.mark.parametrize(("authored", "canonical"), _REPAIRED.values(), ids=_REPAIRED.keys())
def test_each_list_shape_reaches_its_one_spacing(authored: str, canonical: str) -> None:
    """A broken shape is found and repaired, and the repair is a fixed point."""
    assert spacing_violations(authored)
    assert canonical_spacing(authored) == canonical
    assert spacing_violations(canonical) == {}
    assert canonical_spacing(canonical) == canonical


@pytest.mark.parametrize("text", _CONFORMING.values(), ids=_CONFORMING.keys())
def test_a_conforming_list_and_a_fenced_example_keep_their_bytes(text: str) -> None:
    """Only list structure decides; a fenced example's blank lines are its content."""
    assert spacing_violations(text) == {}
    assert canonical_spacing(text) == text


def test_the_repair_moves_only_blank_lines_and_renders_a_tight_list() -> None:
    """The words stay, the violation names its line, and the repaired list renders tight."""
    authored = "# Steps\n\n- one\n\n- two\n\n- three\n"
    canonical = canonical_spacing(authored)

    assert spacing_violations(authored) == {4: 0, 6: 0}
    assert canonical.split() == authored.split()
    assert "<p>" not in MarkdownIt("commonmark").render(canonical)
