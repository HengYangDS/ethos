from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

import ethos.adapters.repo.dirty.change_provenance as provenance


@pytest.mark.parametrize(
    ("returncode", "stdout", "expected"),
    [
        (0, "src/a.py\ntests/test_a.py\n", ("src/a.py", "tests/test_a.py")),
        (1, "ignored\n", ()),
    ],
)
def test_committed_change_paths_fail_closed_on_git_result(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stdout: str,
    expected: tuple[str, ...],
) -> None:
    calls = []

    def run_git(_root, *arguments, **kwargs):
        calls.append((arguments, kwargs))
        return SimpleNamespace(returncode=returncode, stdout=stdout)

    monkeypatch.setattr(provenance, "run_git", run_git)
    assert provenance.committed_change_paths(tmp_path, "candidate/dev") == expected
    assert calls == [(("diff", "--name-only", "candidate/dev...HEAD"), {"check": False})]


def test_change_scope_deduplicates_committed_and_dirty_paths(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        provenance,
        "committed_change_paths",
        lambda _root, base: ("shared", "committed") if base == "candidate/dev" else (),
    )
    monkeypatch.setattr(provenance, "changed_paths", lambda _root: ("shared", "dirty"))

    assert provenance.change_scope_paths(tmp_path, base_ref="candidate/dev") == (
        "shared",
        "committed",
        "dirty",
    )
    assert provenance.change_scope_paths_from_status(
        tmp_path,
        {"role": "work_lane", "role_policy": {"candidate_branch": "candidate/dev"}},
    ) == ("shared", "committed", "dirty")
    assert provenance.change_scope_paths_from_status(
        tmp_path,
        {"role": "accepted_root", "role_policy": {"candidate_branch": "candidate/dev"}},
    ) == ("shared", "dirty")


def test_dirty_provenance_classifies_git_porcelain_and_temporary_probe(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    probe = tmp_path / "tests/test_probe.py"
    probe.parent.mkdir()
    probe.write_text("# TEMP PROBE\n", encoding="utf-8")
    output = (
        " M tracked.py\n"
        "D  deleted.py\n"
        "UU conflicted.py\n"
        "R  old.py -> renamed.py\n"
        "?? tests/test_probe.py"
    )
    monkeypatch.setattr(provenance, "git_stdout_checked", lambda *_args: output)

    report = provenance.dirty_provenance(tmp_path)

    assert report["state"] == "dirty"
    assert report["summary"] == {
        "tracked": 2,
        "untracked": 1,
        "deleted": 1,
        "conflicted": 1,
        "unavailable": 0,
    }
    assert [entry["path"] for entry in report["entries"]] == [
        "tracked.py",
        "deleted.py",
        "conflicted.py",
        "renamed.py",
        "tests/test_probe.py",
    ]
    assert report["temporary_probes"] == {
        "count": 1,
        "paths": ["tests/test_probe.py"],
        "truncated": False,
    }


@pytest.mark.parametrize(
    "error",
    [OSError("git unavailable"), subprocess.CalledProcessError(1, "git", stderr="bad repo")],
)
def test_dirty_provenance_reports_unavailable_observation(
    tmp_path, monkeypatch: pytest.MonkeyPatch, error: BaseException
) -> None:
    def fail(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(provenance, "git_stdout_checked", fail)
    report = provenance.dirty_provenance(tmp_path)

    assert report["dirty"] is True
    assert report["state"] == "unavailable"
    assert report["summary"]["unavailable"] == 1
    assert report["entries"] == []
    assert report["error"] in {"git unavailable", "bad repo"}


def test_working_overlay_digest_omits_head_baseline(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    def run_git(_root, *arguments, **_kwargs):
        calls.append(arguments)
        return SimpleNamespace(stdout=b"")

    monkeypatch.setattr(provenance, "run_git", run_git)
    assert len(provenance.working_overlay_sha256(tmp_path)) == 64
    assert calls == [
        ("diff", "--binary", "--"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
        ("diff", "--binary", "--"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    ]
