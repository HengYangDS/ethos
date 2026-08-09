from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.patch_admission as admission

if TYPE_CHECKING:
    from pathlib import Path


def _patch(old: str, new: str, body: str = "+value\n") -> str:
    return f"diff --git a/{old} b/{new}\n--- a/{old}\n+++ b/{new}\n@@ -0,0 +1 @@\n{body}"


def _admit_to_postimage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admission, "_patch_applies", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(admission, "_baseline_exact_scope_paths", lambda *_args: {"safe.txt"})
    monkeypatch.setattr(
        admission,
        "_baseline_product_references",
        lambda *_args: {
            kind: frozenset()
            for kind in ("import", "distribution", "executable", "reference", "command", "value")
        },
    )


def test_patch_admission_rejects_absolute_and_escaping_preimages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _admit_to_postimage(monkeypatch)
    for old in ("/absolute", "../escape"):
        patch = _patch(old, "safe.txt")
        report = admission.patch_admission(
            root=tmp_path,
            requested_paths=("safe.txt",),
            baseline_head="a" * 40,
            patch=patch,
        )
        assert report["reason"] == "prewrite_patch_postimage_failed"


def test_patch_admission_rejects_missing_preimage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _admit_to_postimage(monkeypatch)
    report = admission.patch_admission(
        root=tmp_path,
        requested_paths=("safe.txt",),
        baseline_head="a" * 40,
        patch=_patch("missing.txt", "safe.txt"),
    )
    assert report["reason"] == "prewrite_patch_postimage_failed"


def test_patch_admission_rejects_escaping_postimage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _admit_to_postimage(monkeypatch)
    source = tmp_path / "safe.txt"
    source.write_text("old\n", encoding="utf-8")
    monkeypatch.setattr(admission, "_baseline_exact_scope_paths", lambda *_args: {"../escape"})
    report = admission.patch_admission(
        root=tmp_path,
        requested_paths=("../escape",),
        baseline_head="a" * 40,
        patch=_patch("safe.txt", "../escape"),
    )
    assert report["reason"] == "prewrite_patch_postimage_failed"


def test_patch_admission_rejects_nonlist_scope_and_failed_postimage_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(admission, "git_stdout", lambda *_args: "carrier/commitment.toml")
    assert admission._baseline_exact_scope_paths(tmp_path, "head") == set()  # noqa: SLF001

    source = tmp_path / "safe.txt"
    source.write_text("old\n", encoding="utf-8")
    patch = _patch("safe.txt", "safe.txt")
    monkeypatch.setattr(admission, "_patch_applies", lambda *_args, **_kwargs: False)
    with pytest.raises(ValueError, match="postimage application failed"):
        admission._patch_references(tmp_path, patch, [{"old_path": "safe.txt", "path": "safe.txt"}])  # noqa: SLF001
