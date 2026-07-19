from __future__ import annotations

import ethos_core.measure as measure
from ethos_core.measure import effective_code_lines


def test_effective_code_lines_excludes_comments_blanks_docstrings_and_padding_strings(tmp_path):
    path = tmp_path / "sample.py"
    path.write_text(
        '''"""module doc
second line
"""

# full-line comment
import os  # inline comments are still code lines

class Example:
    """class doc"""

    def method(self):
        """method doc
        second line
        """
        "padding string"
        value = 1
        return value
''',
        encoding="utf-8",
    )

    assert effective_code_lines(path) == 5


def test_effective_code_lines_syntax_error_falls_back_to_nonblank_noncomment_count(tmp_path):
    path = tmp_path / "broken.py"
    path.write_text(
        "# ignored\n\nif True print('broken')\n\"not a parsed padding string\"\n",
        encoding="utf-8",
    )

    assert effective_code_lines(path) == 2


def test_effective_code_lines_reuses_immutable_source_measurement(tmp_path, monkeypatch):
    path = tmp_path / "sample.py"
    path.write_text(f"value = 1  # {tmp_path.name}\n", encoding="utf-8")
    calls = 0
    original = measure.ast.parse

    def counted(source: str, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original(source, *args, **kwargs)

    monkeypatch.setattr(measure.ast, "parse", counted)

    assert effective_code_lines(path) == 1
    assert effective_code_lines(path) == 1
    assert calls == 1
