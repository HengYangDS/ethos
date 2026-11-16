"""Each journey stage runs in one fresh environment; the offline one installs verified bytes."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import tools.ci.delivery.acceptance.acquisition as acquisition
import tools.ci.delivery.acceptance.journey as journey
from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.materialization.effect import remove_generated_tree
from tools.ci.delivery.acceptance import host_environment
from tools.ci.delivery.acceptance.invocation import run_native

if TYPE_CHECKING:
    from collections.abc import Callable

EXECUTABLES = ("git", "ssh-keygen")
# A child that prints its whole environment.
PRINT = (sys.executable, "-c", "import json, os; print(json.dumps(dict(os.environ)))")
# What a host shows and no journey child may see; each value is fake.
SUPPLY = "ETHOS_CI_TOOL_CACHE_DIR"
HOST = {
    SUPPLY: "/fake/supply",
    "GH_TOKEN": "fake",
    "SSH_AUTH_SOCK": "/fake/agent",
    "XDG_DATA_HOME": "/fake",
    "DISPLAY": ":0",
}
# What a child's own runtime adds to an environment that lacks it.
RUNTIME = {"LC_CTYPE", "__CF_USER_TEXT_ENCODING"}
# Every variable a journey child is given: fresh directories and a file under the owner's root.
FRESH = {"HOME": "home", "TMPDIR": "tmp", "PATH": "bin", "GIT_TEMPLATE_DIR": "templates"}
FRESH |= {"GIT_CONFIG_GLOBAL": "gitconfig"}
DECLARED = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_ATTR_NOSYSTEM": "1"}
DIGEST = hashlib.sha256(b"archive").hexdigest()
ENTRY = {"version": "1.2.3", "archive": "assets/a.tar.gz", "sha256": DIGEST, "archives": {}}
posix = pytest.mark.skipif(os.name == "nt", reason="a fresh home and linked path are POSIX")
_GLOBAL = "GIT_CONFIG_GLOBAL"


def _replace(link: Path, target: str = "") -> None:
    """Put a plain file, or a link to `target`, where a declared link was."""
    link.unlink()
    link.symlink_to(target) if target else link.touch()


@posix
def test_every_child_inherits_or_is_handed_the_same_fresh_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A child sees a new home and temporary directory, isolated Git and linked executables.

    Nothing else of the host reaches it: no agent socket, forge token or desktop variable. The
    place of the host's tool supply is shown to this process for one block alone, and to no
    child after it; the host's environment returns afterwards. Removing the environment
    leaves the host's executables where they are.
    """
    for name, value in HOST.items():
        monkeypatch.setenv(name, value)
    host, root, temporary = dict(os.environ), tmp_path / "environment", tempfile.gettempdir()
    with host_environment.hermetic_environment(root, EXECUTABLES) as environment:
        with host_environment.host_supply({SUPPLY: HOST[SUPPLY]}):
            prepared = json.loads(run_command(tmp_path, PRINT).stdout)
        inherited = json.loads(run_command(tmp_path, PRINT).stdout)
        handed = json.loads(
            run_command(tmp_path, PRINT, env=environment, inherit_environment=False).stdout
        )
        resolved = {name: shutil.which(name) for name in EXECUTABLES}
        assert tempfile.gettempdir() == environment["TMPDIR"]
    assert environment == DECLARED | {name: str(root / part) for name, part in FRESH.items()}
    for child in (inherited, handed):
        assert {name: child[name] for name in environment} == environment
        assert child.keys() - environment.keys() <= RUNTIME
    # A command of the preparation inherits the supply's place, and no later child does.
    supplied = (prepared[SUPPLY], SUPPLY in inherited, SUPPLY in handed)
    assert supplied == ("/fake/supply", False, False)
    assert resolved == {name: str(root / "bin" / name) for name in EXECUTABLES}
    assert (dict(os.environ), tempfile.gettempdir()) == (host, temporary)
    sources = [Path(link).resolve() for link in resolved.values()]
    remove_generated_tree(root)
    assert (root.exists(), [source.is_file() for source in sources]) == (False, [True, True])


@posix
def test_git_starts_from_its_link_without_host_configuration_or_templates(tmp_path: Path) -> None:
    """Only the repository's own configuration applies, and a new repository gets no template."""
    repo = tmp_path / "repo"
    with host_environment.hermetic_environment(tmp_path / "environment", EXECUTABLES) as fresh:
        run_native("git", "init", "--quiet", str(repo), cwd=tmp_path, env=fresh)
        scopes = run_native("git", "config", "--list", "--show-scope", cwd=repo, env=fresh)
    assert {line.split()[0] for line in scopes.splitlines()} == {"local"}
    assert not (repo / ".git/hooks").exists()


@posix
def test_the_fixture_adopter_is_built_and_signed_inside_the_fresh_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Its Git commands get the journey's environment too: no template, a commit that verifies."""
    built: list[Path] = []
    upgrade = journey.runtime_acceptance
    monkeypatch.setattr(
        upgrade, "prove_retained_upgrade", lambda _s, repo, **_k: built.append(repo)
    )
    with host_environment.hermetic_environment(tmp_path / "environment", EXECUTABLES) as fresh:
        journey.prove_upgrade(None, None, tmp_path / "store", environment=fresh)
        signed = run_native("git", "log", "--format=%G?", cwd=built[0], env=fresh)
    assert (signed, (built[0] / ".git/hooks").exists()) == ("G", False)


def test_the_supply_block_restores_every_name_it_set_also_when_it_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A name that the process held before keeps its value; one it did not hold is gone again."""
    monkeypatch.setenv("HELD", "before")
    monkeypatch.delenv(SUPPLY, raising=False)
    shown = {SUPPLY: "/fake/supply", "HELD": "inside"}
    with host_environment.host_supply(shown):
        inside = {name: os.environ[name] for name in shown}
    after = (os.environ.get(SUPPLY), os.environ.get("HELD"))
    with pytest.raises(RuntimeError), host_environment.host_supply(shown):
        raise RuntimeError
    assert (inside, after) == (shown, (None, "before"))
    assert (os.environ.get(SUPPLY), os.environ.get("HELD")) == (None, "before")


def test_a_windows_stage_keeps_its_minimal_path_and_refuses_what_it_does_not_hold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows links nothing, so a declared executable outside the minimal path is refused by name.

    The path gains no directory for it: a directory would show a child every neighbour of that
    executable. A stage that starts still names a variable beyond its declaration.
    """
    client = tmp_path / "forge/client"
    client.parent.mkdir()
    client.touch(mode=0o755)
    monkeypatch.setenv("PATH", os.pathsep.join((os.environ["PATH"], str(client.parent))))
    monkeypatch.setenv("SYSTEMROOT", str(tmp_path / "windows"))
    windows = SimpleNamespace(name="nt", environ=os.environ, pathsep=os.pathsep)
    monkeypatch.setattr(host_environment, "os", windows)
    refused, started = tmp_path / "refused", tmp_path / "started"
    stage = host_environment.hermetic_environment
    unresolved = "cannot resolve client: a Windows stage's path holds"
    with pytest.raises(RuntimeError, match=unresolved), stage(refused, ("client",)):
        pass
    with stage(started, EXECUTABLES) as declared:
        clean = host_environment.hermetic_gap(started, EXECUTABLES)
        os.environ.update(GH_TOKEN="fake")
        shown = host_environment.hermetic_gap(started, EXECUTABLES)
    assert (refused.exists(), str(client.parent) in declared["PATH"]) == (False, False)
    assert (clean, shown) == ("", "GH_TOKEN")


# Each way a stage's environment can show a child more than was declared, and what is named.
CHANGES: dict[str, tuple[Callable[[Path], object], str]] = {
    "nothing": (lambda _root: None, ""),
    "a forge token": (lambda _root: os.environ.update(GH_TOKEN="fake"), "GH_TOKEN"),
    "an agent socket": (lambda _root: os.environ.update(SSH_AUTH_SOCK="/fake"), "SSH_AUTH_SOCK"),
    "a desktop variable": (lambda _root: os.environ.update(XDG_DATA_HOME="/fake"), "XDG_DATA_HOME"),
    "the host's home": (lambda _root: os.environ.update(HOME="/fake"), "HOME"),
    "system attributes": (lambda _root: os.environ.pop("GIT_ATTR_NOSYSTEM"), "GIT_ATTR_NOSYSTEM"),
    "a used home": (lambda root: (root / "home/.gitconfig").touch(), "HOME"),
    "a used temporary directory": (lambda root: (root / "tmp/left").touch(), "TMPDIR"),
    "a template": (lambda root: (root / "templates/hooks").mkdir(), "GIT_TEMPLATE_DIR"),
    "global configuration": (lambda root: (root / "gitconfig").write_text("[a]\n"), _GLOBAL),
    "an undeclared executable": (lambda root: (root / "bin/gh").symlink_to(sys.executable), "PATH"),
    "a copied executable": (lambda root: _replace(root / "bin/git"), "PATH"),
    "an absent executable": (lambda root: _replace(root / "bin/git", "/absent/git"), "PATH"),
}


@posix
@pytest.mark.parametrize("case", CHANGES)
def test_the_owner_names_what_shows_a_child_more_than_it_declared(
    tmp_path: Path, case: str
) -> None:
    """A variable, a file or an executable beyond the declared environment is named."""
    root, (change, gap) = tmp_path / "environment", CHANGES[case]
    with host_environment.hermetic_environment(root, EXECUTABLES):
        change(root)
        assert host_environment.hermetic_gap(root, EXECUTABLES) == gap


@pytest.mark.parametrize(
    ("stored", "gap"),
    [(b"archive", ""), (b"changed", "^release_journey_archive_tampered:a.tar.gz$")],
)
def test_qualification_installs_only_an_archive_that_still_matches_its_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stored: bytes, gap: str
) -> None:
    """Each install hashes its archive again; one that changed since acquisition stays out."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets/a.tar.gz").write_bytes(stored)
    manifest, installed = tmp_path / "manifest.json", []
    manifest.write_text(json.dumps({"releases": [ENTRY | {"verified": "attested"}]}))
    monkeypatch.setattr(
        journey,
        "install_archive",
        lambda archive, *_a, sha256, **_k: installed.append((archive, sha256)),
    )
    (release,) = acquisition.read_manifest(manifest)
    with pytest.raises(ValueError, match=gap) if gap else nullcontext():
        journey.install_acquired(release, tmp_path / "home", mise=tmp_path, environment={})
    # Mise is given the manifest's digest, so bytes that change after this check stay out too.
    assert installed == ([] if gap else [(release.archive, DIGEST)])


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        "[]",
        json.dumps({"releases": []}),
        json.dumps({"releases": [ENTRY]}),
        json.dumps({"releases": [ENTRY | {"verified": "attested", "url": ""}]}),
        json.dumps({"releases": [ENTRY | {"verified": "attested", "archive": "../a.tar.gz"}]}),
    ],
)
def test_qualification_refuses_a_manifest_that_is_not_whole(
    tmp_path: Path, text: str | None
) -> None:
    """An absent, unparsable, empty, partial or extended one, or one that leaves its directory."""
    manifest = tmp_path / "manifest.json"
    if text is not None:
        manifest.write_text(text)
    with pytest.raises(ValueError, match=r"^release_journey_manifest_invalid$"):
        acquisition.read_manifest(manifest)
