"""`ethos hook bind-trust` binds the one commit trust input an operator supplies, or nothing."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

import ethos.application.hook.commit_trust as commit_trust
from ethos.adapters.repo.trust_anchor.filesystem import protected_from_untrusted_write
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

_ANCHOR, _MATERIAL = "ETHOS_COMMIT_TRUST_ANCHOR", "ETHOS_COMMIT_ALLOWED_SIGNERS"
_TRUST = "fixture-controlled public trust"
_AMBIGUOUS, _FAILED = "ci_commit_trust_inputs_ambiguous", "ci_commit_trust_projection_failed"
_DENIED = "git_object_trust_anchor_protection_failed:denied"


@pytest.fixture
def job(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """A fixture checkout and a protected anchor outside it, with no ambient trust input."""
    repo = init_git_repo(tmp_path / "repo")
    anchor = tmp_path / "trust/allowed-signers"
    anchor.parent.mkdir(mode=0o700)
    anchor.write_text(f"{_TRUST}\n")
    anchor.chmod(0o600)
    for name in (_ANCHOR, _MATERIAL):
        monkeypatch.delenv(name, raising=False)
    # `tempfile` keeps the temporary root it first found; the variable alone cannot move it.
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    return repo, anchor


def _argv(repo: Path, *arguments: str) -> tuple[str, ...]:
    return ("hook", "bind-trust", *arguments, "--root", str(repo), "--json")


@pytest.mark.parametrize("apply", [False, True])
@pytest.mark.parametrize("supplied", ["--anchor", _ANCHOR, _MATERIAL, ""])
def test_the_one_supplied_input_is_previewed_and_only_an_apply_binds_it(
    job, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, supplied: str, *, apply: bool
) -> None:
    """A preview names the anchor and writes nothing; an apply writes the one local setting."""
    repo, anchor = job
    if supplied.startswith("ETHOS"):
        monkeypatch.setenv(supplied, _TRUST if supplied == _MATERIAL else str(anchor))
    flags = (("--anchor", str(anchor)) if supplied == "--anchor" else ()) + ("--apply",) * apply
    replaced = git(repo, "config", "--local", "--get", "gpg.ssh.allowedSignersFile")
    before = git(repo, "config", "--local", "--list")

    result = run_ethos(*_argv(repo, *flags))

    settings = git(repo, "config", "--local", "--list")
    named = result["summary"]["anchor"]
    assert result["summary"]["inputs"] == [supplied] * bool(supplied)
    if not supplied or not apply:
        assert result["state"] == ("planned" if supplied else "unbound")
        assert result["next"]["form"] == ("hook.bind-trust.apply" if supplied else "")
        assert named == ("" if supplied in {_MATERIAL, ""} else str(anchor))
        assert (settings, list(tmp_path.glob("ethos-ci-trust-*"))) == (before, [])
        return
    assert (result["state"], result["next"]["kind"]) == ("bound", "done")
    assert settings == before.replace(replaced, named)
    assert Path(named).read_text(encoding="utf-8").strip() == _TRUST
    assert protected_from_untrusted_write(Path(named))
    assert (Path(named) == anchor) == (supplied != _MATERIAL)


@pytest.mark.parametrize(
    ("case", "source", "gap"),
    [
        ("flagged", _ANCHOR, _AMBIGUOUS),
        ("both", _ANCHOR, _AMBIGUOUS),
        ("blank", _MATERIAL, "ci_commit_trust_material_missing"),
        ("inside", _ANCHOR, "git_object_trust_anchor_inside_repository"),
        ("unprotected", _ANCHOR, "git_object_trust_anchor_unprotected"),
        ("missing", _ANCHOR, "git_object_trust_anchor_missing"),
        ("locked", _ANCHOR, _FAILED),
        ("locked", _MATERIAL, _FAILED),
        ("denied", _MATERIAL, _DENIED),
    ],
)
def test_a_refused_input_names_its_gap_and_binds_nothing(
    job, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str, source: str, gap: str
) -> None:
    """A preview and an apply refuse alike; a failed write or read-back leaves no anchor behind."""
    repo, anchor = job
    if case == "inside":
        anchor = anchor.rename(repo / anchor.name)
    elif case == "unprotected":
        anchor.chmod(0o666)
    elif case == "missing":
        anchor.unlink()
    elif case == "locked":
        (repo / ".git/config.lock").touch()
    elif case == "denied":
        monkeypatch.setattr(
            commit_trust, "protect_for_current_identity", Mock(side_effect=OSError(gap))
        )
    material = " \n" if case == "blank" else _TRUST
    monkeypatch.setenv(source, str(anchor) if source == _ANCHOR else material)
    if case == "both":
        monkeypatch.setenv(_MATERIAL, material)
    flags = ("--anchor", str(anchor)) if case == "flagged" else ()
    before = (repo / ".git/config").read_bytes()

    applied = run_ethos_blocked(*_argv(repo, *flags, "--apply"))

    assert (applied["state"], applied["required_gaps"]) == ("blocked", [gap])
    assert (repo / ".git/config").read_bytes() == before
    assert not list(tmp_path.glob("ethos-ci-trust-*"))
    if case not in {"locked", "denied"}:
        assert run_ethos_blocked(*_argv(repo, *flags))["required_gaps"] == [gap]
