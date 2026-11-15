"""`ethos lane upgrade-from` derives a release's predecessors from the host's recorded subjects."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.host_store import record_consumer
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.toolchain.mise import MISE_CONFIG
from ethos.repository.release.identity import build_identity
from ethos.repository.release.pin import pin_line
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_tree
from tests.support.runtime_scenarios import fixture_runtime_generation

DAY = 24 * 60 * 60
EPOCH = 2_000_000_000
HISTORY = ("beta.12", "beta.11", "beta.10", "beta.3", "beta.1", "alpha.28")
CHANGELOG = "# Changelog\n\n## [Unreleased]\n\n" + "".join(
    f"## [0.2.0-{stage}] - 2026-11-01\n\n### Fixed\n\n- Correct the result.\n\n"
    for stage in HISTORY
)
DERIVED = {
    "0.2.0-beta.11": "attested-main",
    "0.2.0-beta.10": "attested-main",
    "0.2.0-beta.3": "checksum",
    "0.2.0-beta.1": "attested-main",
}
TABLE = "[release.upgrade_from]\n" + "".join(
    f'"{name}" = "{kind}"\n' for name, kind in DERIVED.items()
)
_INCOMPLETE = "release_upgrade_from_incomplete:0.2.0-beta.3,0.2.0-beta.1"
_INVALID = "release_upgrade_from_invalid"
CASES = [
    ("undeclared", "", "0.2.0-beta.10", ["release_upgrade_from_empty"]),
    ("empty", "[release.upgrade_from]\n", "0.2.0-beta.10", ["release_upgrade_from_empty"]),
    ("incomplete", TABLE.partition('"0.2.0-beta.3"')[0], "0.2.0-beta.10", [_INCOMPLETE]),
    ("complete", TABLE + '"0.1.0" = "checksum"\n', "0.2.0-beta.10", []),
    ("another-class", TABLE.replace("checksum", "attested"), "0.2.0-beta.10", [_INVALID]),
    ("development-build", TABLE, "", []),
]


def _pinned(stage: str, major: str = "") -> dict[str, str]:
    """Pin one prerelease of 0.2.0, or with a leading digit of a version that ends in its name."""
    return {MISE_CONFIG: f"[tools]\n{pin_line(major + '0.2.0-' + stage)}\n"}


def _installation(tmp_path: Path) -> Path:
    """The one installation of this test's host store, which records its consumers."""
    installation = tmp_path / "user-data/ethos/installations" / ("0" * 16)
    installation.mkdir(parents=True, exist_ok=True)
    return installation


def _repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, *trees: tuple[int, dict[str, str]]
) -> Path:
    """Record as a consumer one repository whose accepted branch gained each tree on its day."""
    repo = init_git_repo(tmp_path / name)
    for day, tree in trees:
        monkeypatch.setenv("GIT_COMMITTER_DATE", f"{EPOCH + day * DAY} +0000")
        write_tree(repo, tree)
        commit_fixture(repo, "chore: move the tree")
    record_consumer(_installation(tmp_path), Path(git_common_dir(repo)))
    return repo


def _select(repo: Path, product: str) -> str:
    """Select a build as the repository's `CURRENT`: a release, or with no name a development build.

    Returns the name that the build goes by as a predecessor.
    """
    store = Path(git_common_dir(repo)) / "ethos/runtime"
    store.mkdir(parents=True)
    build = build_identity(
        product=product or "0.2.0-beta.12",
        release=bool(product),
        source_commit="a" * 40,
        source_tree="b" * 40,
    )
    generation = fixture_runtime_generation(
        store / "new", "selected", repository_private=False, build=build
    )
    activate_runtime(store.parents[1], generation)
    return product or build.distribution_version


@pytest.mark.parametrize("case", CASES, ids=[case[0] for case in CASES])
def test_a_lane_derives_what_its_release_upgrades_from(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: tuple[str, str, str, list[str]]
) -> None:
    """The subjects are read from the host's records; the result names no repository.

    One subject moved its pin back to a release whose name begins another's and ends a third's,
    then changed its configuration again: its bump is the commit that changed the pin. One holds
    the older form at the window's edge and one is a day outside the window. One declares no pin
    and is a subject by its selection, with no time. Three declare a pin that cannot be read:
    both keys, a version prefix and text that is not TOML. Each of those pins names no release
    and is counted by itself, and its repository is a subject by its selection. One has neither
    a pin nor a selection, one is gone and one record is torn: each is unread. The releasing
    repository is recorded too, with the newest bump, and is no subject of itself. The rows come
    newest bump first, whatever the paths. A selected build that the changelog does not list
    refuses nothing.
    """
    _name, record, selected, gaps = case
    moved = [(10, "beta.1"), (20, "beta.10"), (30, "beta.1"), (40, "beta.1")]
    first = _repository(
        tmp_path,
        monkeypatch,
        "z",
        *((day, _pinned(stage, "1" * (day == 30))) for day, stage in moved),
        (41, {MISE_CONFIG: _pinned("beta.1")[MISE_CONFIG] + 'node = "26"\n'}),
    )
    older = '[tools."http:ethos"]\nversion = "0.2.0-beta.3"\n'
    edge = _repository(tmp_path, monkeypatch, "b", (26, {MISE_CONFIG: older}))
    outside = _repository(tmp_path, monkeypatch, "a", (25, _pinned("alpha.28")))
    alone = _repository(tmp_path, monkeypatch, "d", (41, {"notes.txt": "no pin\n"}))
    _select(alone, "0.2.0-beta.10")
    _repository(tmp_path, monkeypatch, "f", (41, {"notes.txt": "no pin\n"}))
    broken = {
        "g": _pinned("beta.3")[MISE_CONFIG] + older,
        "h": "[tools]\n" + pin_line("0.2"),
        "i": "[tools\n",
    }
    for name, text in broken.items():
        unreadable = _repository(tmp_path, monkeypatch, name, (41, {MISE_CONFIG: text}))
        _select(unreadable, "0.2.0-beta.10")
    shutil.rmtree(_repository(tmp_path, monkeypatch, "e", (41, _pinned("beta.11"))))
    (_installation(tmp_path) / "consumers/torn").write_text("relative\n", encoding="utf-8")
    current = _select(first, selected)
    binding = '[release]\nmirror = "independent"\n\n' + record
    release = {"VERSION": "0.2.0-beta.12\n", "CHANGELOG.md": CHANGELOG, **_pinned("alpha.28")}
    release[".ethos/release.toml"] = binding
    product = _repository(tmp_path, monkeypatch, "product", (41, release))

    result = run_ethos("lane", "upgrade-from", "--root", product.as_posix(), "--json")

    assert result["required_gaps"] == gaps
    assert result["verdict"] == ("block" if gaps else "pass")
    assert bool(result["next_action"]) is bool(gaps)
    if gaps == [_INVALID]:
        return
    data, listed = result["data"], current in DERIVED
    assert (data["release"], data["derived"], data["unread"]) == ("0.2.0-beta.12", DERIVED, 3)
    assert list(data["derived"]) == list(DERIVED)
    assert data["counts"] == {"github": 1, "http": 1, "selection": 4}
    assert data["subjects_with_unreadable_pin"] == 3
    assert list(data["named"]) == ["0.2.0-beta.12", *DERIVED]
    assert list(data["named"].values()) == [
        {"pin": 0, "selection": 0},
        {"pin": 0, "selection": 0},
        {"pin": 0, "selection": 4 + listed},
        {"pin": 1, "selection": 0},
        {"pin": 1, "selection": 0},
    ]
    assert data["unlisted"] == ({} if listed else {current: {"pin": 0, "selection": 1}})
    assert [row["form"] for row in data["subjects"][4:]] == ["unreadable"] * 3
    assert [tuple(row.values()) for row in data["subjects"][:4]] == [
        (git(first, "rev-parse", "dev"), "github", "0.2.0-beta.1", current, EPOCH + 40 * DAY, True),
        (git(edge, "rev-parse", "dev"), "http", "0.2.0-beta.3", "", EPOCH + 26 * DAY, True),
        (git(outside, "rev-parse", "dev"), "github", "0.2.0-alpha.28", "", EPOCH + 25 * DAY, False),
        (git(alone, "rev-parse", "dev"), "", "", "0.2.0-beta.10", None, True),
    ]


def test_a_host_without_a_store_derives_the_previous_release_alone(tmp_path: Path) -> None:
    """No recorded consumer is no subject: the release still upgrades from its predecessor."""
    product = init_git_repo(tmp_path / "product")
    write_tree(product, {"VERSION": "0.2.0-beta.12\n", "CHANGELOG.md": CHANGELOG})
    commit_fixture(product, "chore: prepare the release")
    data = run_ethos("lane", "upgrade-from", "--root", product.as_posix(), "--json")["data"]
    assert (data["derived"], data["subjects"]) == ({"0.2.0-beta.11": "attested-main"}, [])
    assert data["unread"] == 0
