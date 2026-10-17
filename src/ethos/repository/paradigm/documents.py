"""Document conventions of the repository paradigm.

Documents under the profile docs root begin with plain YAML front matter, and a
repository that keeps decision records names each with the shared grammar.
"""

from __future__ import annotations

import posixpath
import re
from typing import TYPE_CHECKING

from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.gap import tracked_text
from ethos.repository.profile import RepositoryRoots
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import RepositoryParadigm

_RECORD = re.compile(r"(?i)a?dr[-_ ]?(\d+)[-_ ]*(.*)\.md")
_WORD = re.compile(r"[a-z0-9]+")


def document_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Report documents without leading front matter and nonstandard decision record names."""
    profile = load_repository_profile(root)
    roots = profile.declaration.roots if profile.declaration else RepositoryRoots()
    prefix = f"{roots.docs.rstrip('/')}/"
    for path in sorted(entry for entry in tracked if entry.startswith(prefix)):
        if not path.endswith(".md"):
            continue
        opening = (tracked_text(root, path, tracked) or "").splitlines()[:2]
        if opening[:1] == ["---"]:
            continue
        repair = (
            f"remove the <!-- and --> lines so YAML front matter starts {path}"
            if opening == ["<!--", "---"]
            else f"begin {path} with YAML front matter carrying subject, role, state and relations"
        )
        yield ParadigmGap("front-matter", path, repair)
    yield from _decision_record_gaps(paradigm, tracked)


def is_decision_record(basename: str) -> bool:
    """Return whether a basename names a numbered decision record, which its grammar judges."""
    return _RECORD.fullmatch(basename) is not None


def _decision_record_gaps(
    paradigm: RepositoryParadigm, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Name every numbered decision record dr-NNNN-<topic>.md, wherever it is kept."""
    grammar = re.compile(paradigm.documents.decision_record_name)
    for path in sorted(tracked):
        directory, basename = posixpath.split(path)
        record = _RECORD.fullmatch(basename)
        if record is None or grammar.fullmatch(basename):
            continue
        if not path.startswith(paradigm.immutable_roots):
            topic = "-".join(_WORD.findall(record.group(2).lower())) or "<topic>"
            name = posixpath.join(directory, f"dr-{int(record.group(1)):04d}-{topic}.md")
            yield ParadigmGap("decision-record", path, f"rename {path} to {name}")
