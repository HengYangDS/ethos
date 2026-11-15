"""The product's release tag needs a complete policy, and its installed release is accepted once."""

from __future__ import annotations

import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.application.land.release_acceptance as acceptance
import ethos.application.publication.inspection as inspection
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.application.catalog import invoke
from ethos.application.console import run_console
from ethos.application.publication.operation import publish_repository
from ethos.contracts.codes.gaps import repair_for
from ethos.contracts.digest import file_sha256
from ethos.repository.release.configuration import release_ref_policy
from ethos.repository.release.identity import build_identity
from ethos.repository.release.identity import build_identity_bytes
from ethos.repository.release.resources import BUILD_IDENTITY_RESOURCE
from ethos.repository.release.resources import WHEEL_RESOURCE_ROOT
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_file
from tests.support.governed_repository import write_test_profile

_TAG = ("release_publication",)
_WHEEL = "ethos-0.1.0-py3-none-any.whl"
# Each refusal: what differs from an acceptable installed release, and the gap it names.
_REFUSALS = [
    ({"product": None}, "release_installation_absent"),
    ({"release": False}, "release_installation_absent"),
    ({"product": "0.0.9"}, "release_installation_older:0.0.9"),
    ({"product": "0.2.0"}, "release_installation_newer:0.2.0"),
    ({"tag": False}, "release_tag_missing:v0.1.0"),
    ({"commit": "e" * 40}, "release_wheel_build_identity_stale"),
    ({"listed": False}, f"accepted_release_checksum_mismatch:{_WHEEL}"),
    ({"sums": False}, "release_acceptance_input_unreadable"),
    ({"profile": "adopter"}, "release_acceptance_product_only"),
]


@pytest.mark.parametrize(
    ("profile", "roles", "blocked"),
    [("ethos", _TAG, True), ("ethos", ("accepted_root",), False), ("adopter", _TAG, False)],
)
def test_only_the_product_root_owes_the_release_policy_for_a_release_tag(
    tmp_path: Path, profile: str, roles: tuple[str, ...], *, blocked: bool
) -> None:
    """A root with nothing but its profile holds every policy gap; only the product reports them."""
    write_test_profile(tmp_path, profile_id=profile)
    report = release_ref_policy(tmp_path, roles)
    assert (report["verdict"], bool(report.get("next_action"))) == (
        "block" if blocked else "pass",
        blocked,
    )
    assert ("protected_tags_policy_missing" in report["required_gaps"]) is blocked
    assert release_ref_policy(Path.cwd(), _TAG)["required_gaps"] == []


def test_publish_refuses_a_release_tag_with_the_policy_gap_and_its_next_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The publication reads the policy for its targets' roles, and a gap blocks with its repair."""
    repo = init_git_repo(tmp_path / "repo")
    write_file(repo / ".ethos/release.toml", '[protected_refs]\ntags = ["v*"]\n')
    gapped = {"verdict": "block", "required_gaps": ["release_file_missing:LICENSE"]}
    seen: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        inspection,
        "release_ref_policy",
        lambda _root, roles: seen.append(roles) or gapped | {"next_action": "repair the policy"},
    )
    # The repository audit has its own next step; this case reads the policy's alone.
    monkeypatch.setattr(
        inspection, "repository_audit_after_admission", lambda *_: {"verdict": "pass"}
    )
    head = git(repo, "rev-parse", "HEAD")
    refused = publish_repository(
        repo, target_refs=("refs/tags/v0.1.0",), probe_remote=True, expect_head=head
    )
    assert seen == [_TAG]
    assert (refused.verdict, refused.next_action) == ("block", "repair the policy")
    assert "release_file_missing:LICENSE" in refused.required_gaps


def _installed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **differs: object) -> Path:
    """Build the product root at release 0.1.0 and the installed release that runs the command."""
    case = {"product": "0.1.0", "release": True, "commit": "", "profile": "ethos"} | differs
    repo = init_git_repo(tmp_path / "repo")
    write_test_profile(repo, profile_id=case["profile"])
    if case.get("tag", True):
        git(repo, "tag", "v0.1.0")
    wheel = tmp_path / _WHEEL
    installed = None
    if case["product"]:
        build = build_identity(
            product=str(case["product"]),
            source_commit=str(case["commit"]) or git(repo, "rev-parse", "HEAD"),
            source_tree=git(repo, "rev-parse", "HEAD^{tree}"),
            release=bool(case["release"]),
        )
        with zipfile.ZipFile(wheel, "w") as archive:
            name = (WHEEL_RESOURCE_ROOT / BUILD_IDENTITY_RESOURCE).as_posix()
            archive.writestr(name, build_identity_bytes(build))
        installed = SimpleNamespace(build=build)
        if case.get("sums", True):
            listed = file_sha256(wheel) if case.get("listed", True) else "0" * 64
            (tmp_path / "SHA256SUMS").write_text(f"{listed}  {_WHEEL}\n", encoding="ascii")
    monkeypatch.setattr(acceptance, "selected_runtime_source", lambda _source: installed)
    monkeypatch.setattr(acceptance, "selected_runtime_wheel", lambda _installed: wheel)
    return repo


@pytest.mark.parametrize(("differs", "gap"), _REFUSALS, ids=[str(case) for case, _ in _REFUSALS])
def test_release_accept_refuses_before_any_effect_and_names_the_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, differs: dict[str, object], gap: str
) -> None:
    """Every refusal leaves the Attestation set and the package store as they were."""
    repo = _installed(tmp_path, monkeypatch, **differs)
    refused = invoke("release accept", repo, {"checksums": tmp_path / "SHA256SUMS", "apply": True})
    assert (refused.verdict, refused.required_gaps, refused.next.kind) == (
        "block",
        (gap,),
        "instruction",
    )
    assert refused.next_action.startswith(repair_for(gap) or "repair the reported gap")
    assert read_attestation_set(repo)[1] == ()
    assert not (repo / ".git/ethos/packages").exists()


def test_release_accept_previews_then_records_once_and_a_second_run_changes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The preview names the apply; the apply binds the checksum file; a repeat is unchanged."""
    repo = _installed(tmp_path, monkeypatch)
    monkeypatch.chdir(tmp_path)
    request = {"checksums": Path("SHA256SUMS")}
    preview = invoke("release accept", repo, request)
    assert (preview.state, preview.next.form) == ("ready", "release.accept.apply")
    assert preview.next.argv[4] == str((tmp_path / "SHA256SUMS").resolve())
    assert read_attestation_set(repo)[1] == ()
    accepted = invoke("release accept", repo, request | {"apply": True})
    root, members = read_attestation_set(repo)
    stored = repo / ".git/ethos/packages" / file_sha256(tmp_path / _WHEEL) / _WHEEL
    identity = members[0].payload.body["identity"]
    assert (accepted.state, accepted.next.kind, len(members)) == ("accepted", "done", 1)
    assert identity["checksums_sha256"] == file_sha256(tmp_path / "SHA256SUMS")
    assert (identity["schema_version"], dict(identity["artifacts"])) == (
        3,
        {_WHEEL: stored.parent.name},
    )
    written = stored.stat().st_mtime_ns
    for again in (request | {"apply": True}, request):
        repeated = invoke("release accept", repo, again)
        assert (repeated.state, repeated.next.kind) == ("unchanged", "done")
    assert (read_attestation_set(repo)[0], stored.stat().st_mtime_ns) == (root, written)


@pytest.mark.parametrize(("argv", "runs"), [(["release", "accept"], True), (["status"], False)])
def test_release_accept_runs_in_the_invoking_installation(
    tmp_path: Path, argv: list[str], *, runs: bool
) -> None:
    """Like the hook installation, it is not re-executed into the repository's selected runtime."""
    repo = init_git_repo(tmp_path / "repo")
    (repo / ".git/ethos/runtime").mkdir(parents=True)
    (repo / ".git/ethos/runtime/CURRENT").write_text("unselectable\n", encoding="utf-8")
    ran: list[int] = []
    failure = run_console([*argv, "--root", str(repo)], lambda: ran.append(1))
    assert (bool(ran), failure is None) == (runs, runs)
