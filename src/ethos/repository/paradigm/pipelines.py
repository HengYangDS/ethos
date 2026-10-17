"""The one pipeline model of a repository that runs CI on several Forges.

Pipelines for more than one Forge are defined once in a model under the model root,
and each Forge's files are generated from it; the repository's `check` verb owns the
drift comparison, so the paradigm requires only the model's presence.
"""

from __future__ import annotations

import fnmatch
import posixpath
from typing import TYPE_CHECKING

from ethos.repository.paradigm.gap import ParadigmGap

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ethos.contracts.paradigm.declaration import RepositoryParadigm


def pipeline_model_gaps(
    paradigm: RepositoryParadigm, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Report pipelines for several Forges that no tracked model under the model root defines."""
    model = paradigm.pipelines
    forges = sorted(
        forge.id
        for forge in model.forge
        if any(_reads(pattern, path) for pattern in forge.files for path in tracked)
    )
    modeled = any(
        path.startswith(model.model_root) and path.endswith(model.model_suffix) for path in tracked
    )
    if len(forges) > 1 and not modeled:
        yield ParadigmGap(
            "pipeline-model",
            model.model_root,
            f"define the pipelines once in a {model.model_suffix} model under {model.model_root} "
            f"and generate {' and '.join(forges)} pipeline files from it; "
            "check fails when one differs",
        )


def _reads(pattern: str, path: str) -> bool:
    """Match a pipeline file in the pattern's own directory, never in a subdirectory."""
    directory, name = posixpath.split(pattern)
    return posixpath.dirname(path) == directory and fnmatch.fnmatchcase(
        posixpath.basename(path), name
    )
