"""Work Lane write admission: whether exact paths may be written, without writing them."""

from pathlib import Path

from ethos.adapters.admission.paths import has_invalid_path_character
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.openspec.selection import selected_change
from ethos.application.catalog import standard_input
from ethos.application.lane.result import lane_result
from ethos.contracts.operations.lane import PrewriteRequest
from ethos.result import EthosResult


def admit_lane_write(root: Path, request: PrewriteRequest) -> EthosResult:
    """Check exact worktree or index write admission without applying it.

    A relative path names one below the root unless it holds a character that no path may hold,
    which the admission then refuses by name. The patch is read from its file, or for `-` is the
    text that the transport read from standard input.
    """
    paths = [
        path if path.is_absolute() or has_invalid_path_character(path.as_posix()) else root / path
        for path in map(Path, request.paths)
    ]
    patch = (
        standard_input()
        if request.patch == "-"
        else Path(request.patch).read_text(encoding="utf-8")
        if request.patch is not None
        else ""
    )
    with selected_change(request.change):
        report = prewrite_guard(
            root=root,
            target=request.target,
            paths=paths,
            editor_root=Path(request.editor_root) if request.editor_root is not None else None,
            require_editor_root=request.require_editor_root,
            patch=patch,
        )
    summary = {"path_count": len(paths), "role": report.get("role", "")}
    return lane_result(
        "lane prewrite", {**report, "path_count": len(paths)}, summary=summary, passed="admitted"
    )
