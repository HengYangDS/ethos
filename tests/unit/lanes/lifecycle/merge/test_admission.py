"""Native merge admission reuses observations only within one exact boundary."""

from __future__ import annotations

import ethos.adapters.mutation.lane_lifecycle.merge as merge_admission
import ethos.adapters.repo.runtime.binding as runtime_binding_owner
from tests.support.ethos_cli_runner import run_ethos
from tests.support.openspec_lifecycle import native_merge_fixture


def test_merge_preview_observes_runtime_once_per_admission(tmp_path, monkeypatch):
    """Reuse one observation within admission, never across effect boundaries."""
    work = native_merge_fixture(tmp_path)
    reads = []
    observe = merge_admission.hook_runtime_binding

    def counted(root, **kwargs):
        reads.append(root)
        return observe(root, **kwargs)

    monkeypatch.setattr(merge_admission, "hook_runtime_binding", counted)
    monkeypatch.setattr(runtime_binding_owner, "hook_runtime_binding", counted)
    assert (
        run_ethos(
            "lane", "refresh-base", "--strategy", "merge", "--mode", "abort", "--json", cwd=work
        )["verdict"]
        == "pass"
    )
    assert reads == [work]
