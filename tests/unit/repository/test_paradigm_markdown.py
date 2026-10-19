"""Markdown layout of the repository paradigm and its deterministic repair."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.repair import paradigm_repair_plan
from tests.support.paradigm import CONFORMING
from tests.support.paradigm import paradigm_report

if TYPE_CHECKING:
    from pathlib import Path

_GUIDE = "content/guide.md"

# The layout the shared Markdown formatter writes for every structure the check reads.
_FORMATTED = """---
subject: sample:guide
---

# Guide

Intro paragraph
wrapped over two lines.

- one
- two
  - nested
  - nested again
- three

1. first

   second paragraph
   - joined list

2. second
   ```sh
   tight code
   ```
3. third

```text
literal


blank lines stay
```

    indented


    code

| a   | b   |
| --- | --- |
| 1   | 2   |

> quote
>
> - quoted
>
> - list

Read [the spec][spec].

[spec]: https://example.com/spec
[other]: https://example.com/other

<!-- prettier-ignore -->
| x  |  y |
|--|--|

<!-- one -->
<!-- two -->

<!-- three -->
"""


def _layout_gaps(report: dict) -> list[dict]:
    return [gap for gap in report["gaps"] if gap["obligation"] == "markdown-layout"]


def test_a_formatted_document_conforms(tmp_path: Path) -> None:
    """Every structure the formatter lays out keeps its separators, literal blocks included."""
    report = paradigm_report(tmp_path, {**CONFORMING, _GUIDE: _FORMATTED})

    assert _layout_gaps(report) == []


@pytest.mark.parametrize(
    ("before", "after", "line"),
    [
        pytest.param(
            "- one\n\n- two\n- three\n", "- one\n- two\n- three\n", 3, id="one-block-item"
        ),
        pytest.param("- one\n\n- two\n\n- three\n", "- one\n- two\n- three\n", 3, id="loose-list"),
        pytest.param(
            "1. first\n\n   more\n2. second\n",
            "1. first\n\n   more\n\n2. second\n",
            4,
            id="multi-block-item",
        ),
        pytest.param(
            "- a\n\n  para\n  ```sh\n  code\n  ```\n- b\n",
            "- a\n\n  para\n\n  ```sh\n  code\n  ```\n\n- b\n",
            4,
            id="multi-block-children",
        ),
        pytest.param(
            "- a\n  - nested\n\n- b\n", "- a\n  - nested\n- b\n", 4, id="item-ending-in-list"
        ),
        pytest.param("# Title\nText.\n", "# Title\n\nText.\n", 2, id="heading"),
        pytest.param("Text.\n- item\n", "Text.\n\n- item\n", 2, id="paragraph-and-list"),
        pytest.param("# Title\n\n\n\nText.\n", "# Title\n\nText.\n", 5, id="repeated"),
        pytest.param("---\na: 1\n---\n# Title\n", "---\na: 1\n---\n\n# Title\n", 4, id="front"),
        pytest.param("---\na: 1\n---\n\n\n# T\n", "---\na: 1\n---\n\n# T\n", 6, id="front-gap"),
        pytest.param("\n\n# Title\n\n\n", "# Title\n", 1, id="edges"),
        pytest.param("# Title", "# Title\n", 1, id="final-newline"),
        pytest.param("\n \n", "", 1, id="blank-document"),
        pytest.param(
            "Text [a].\n\n[a]: https://a.example\n\n[b]: https://b.example\n# Next\n",
            "Text [a].\n\n[a]: https://a.example\n[b]: https://b.example\n\n# Next\n",
            5,
            id="definitions",
        ),
        pytest.param(
            "Text.\n\n\n[a]: https://a.example\n",
            "Text.\n\n[a]: https://a.example\n",
            4,
            id="trailing-definitions",
        ),
        pytest.param(
            "- a\n\n\n  more\n- b\n",
            "- a\n\n  more\n\n- b\n",
            4,
            id="item-children-repeated",
        ),
        pytest.param("<!-- note -->\nText.\n", "<!-- note -->\n\nText.\n", 2, id="html"),
        pytest.param(
            "<!-- prettier-ignore -->\n\n| x |\n|-|\n",
            "<!-- prettier-ignore -->\n| x |\n|-|\n",
            3,
            id="ignored-node",
        ),
        pytest.param(
            "<!-- a -->\n\n\n<!-- b -->\n", "<!-- a -->\n\n<!-- b -->\n", 4, id="html-gap"
        ),
    ],
)
def test_a_separator_off_the_layout_is_repaired(
    tmp_path: Path, before: str, after: str, line: int
) -> None:
    """The gap names the first line whose separator changes; the repair changes only blank lines."""
    report = paradigm_report(tmp_path, {**CONFORMING, _GUIDE: before})
    gaps = _layout_gaps(report)

    assert [gap["carrier"] for gap in gaps] == [_GUIDE]
    assert f"first at line {line}" in gaps[0]["repair"]
    plan = paradigm_repair_plan(tmp_path, [ParadigmGap(**gap) for gap in gaps])
    assert [(edit.path, edit.after) for edit in plan.edits] == [(_GUIDE, after)]
    assert _layout_gaps(paradigm_report(tmp_path, {**CONFORMING, _GUIDE: after})) == []


def test_the_repair_counts_every_changed_separator(tmp_path: Path) -> None:
    """One gap per document reports how many separators the repair changes."""
    report = paradigm_report(tmp_path, {**CONFORMING, _GUIDE: "# A\nText.\n- one\n\n- two\n"})

    assert "3 separators" in _layout_gaps(report)[0]["repair"]


def test_an_empty_document_conforms(tmp_path: Path) -> None:
    """A document without content has no separators and no padding."""
    report = paradigm_report(tmp_path, {**CONFORMING, _GUIDE: ""})

    assert _layout_gaps(report) == []


def test_received_and_archived_documents_keep_their_bytes(tmp_path: Path) -> None:
    """Received documents and immutable archived Changes are not laid out."""
    archived = "openspec/changes/archive/2026-01-01-sample/proposal.md"
    files = {**CONFORMING, archived: "# A\nText.\n", "content/received.md": "# B\nText.\n"}

    report = paradigm_report(tmp_path, files, received=("content/received.md",))

    assert _layout_gaps(report) == []


def test_a_repair_that_would_change_the_structure_stays_report_only(tmp_path: Path) -> None:
    """Dropping the padding before a YAML-like block would turn a break into front matter."""
    report = paradigm_report(tmp_path, {**CONFORMING, _GUIDE: "\n---\na: 1\n---\n"})
    gaps = _layout_gaps(report)

    plan = paradigm_repair_plan(tmp_path, [ParadigmGap(**gap) for gap in gaps])

    assert [gap.carrier for gap in plan.report_only] == [_GUIDE]
    assert plan.edits == ()


def test_a_definition_inside_a_list_item_keeps_its_lines(tmp_path: Path) -> None:
    """Blank lines around a reference definition within an item are not separators to repair."""
    text = "- a\n\n  [x]: https://x.example\n\n  b\n\n- c\n"

    report = paradigm_report(tmp_path, {**CONFORMING, _GUIDE: text})

    assert _layout_gaps(report) == []
