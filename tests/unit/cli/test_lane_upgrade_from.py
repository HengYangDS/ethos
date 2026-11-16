"""`ethos lane upgrade-from` derives a release's predecessors from the host's recorded subjects."""

from __future__ import annotations

import errno
import json
import shutil
from pathlib import Path

import pytest

import ethos.application.lane.repair as lane_repair
import ethos.repository.release.predecessors as predecessors
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.host_store import record_consumer
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.upgrade_from import recorded_upgrade_from
from ethos.adapters.toolchain.mise import MISE_CONFIG
from ethos.contracts.outcome import refusal
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
    data, listed = result["data"], current in DERIVED
    # A record that its reader refuses is no record, and the result still names what to record.
    assert (data["recorded"] is None) is (_name in {"undeclared", "another-class"})
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


_READ = ("0.2.0-beta.10", "0.2.0-beta.3")
# What each case leaves unread: the rows, then the unread consumers and records, the
# installations that record no consumer, and the selections that could not be read.
UNREAD = {
    "torn-records": ([_READ], (2, 0, 0)),
    "no-records": ([_READ], (0, 1, 0)),
    "linked-installation": ([_READ], (0, 0, 0)),
    "linked-beside-its-target": ([_READ], (0, 1, 0)),
    "dangling-link": ([_READ], (0, 1, 0)),
    "linked-file": ([_READ], (0, 0, 0)),
    "no-accepted-branch": ([], (1, 0, 0)),
    "torn-selection": ([(_READ[0], None)], (0, 0, 1)),
}


@pytest.mark.parametrize("case", list(UNREAD))
def test_what_cannot_be_read_is_counted_and_never_read_as_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """Each torn record counts; an installation that records no consumer is counted by itself.

    A linked installation is read as the directory it names, once; a link whose target is gone
    is counted with the installations that record no consumer.
    A repository whose accepted branch cannot be read is unread, not a subject without a pin.
    A selection that cannot be read is counted, and its repository stays a subject by its pin.
    """
    subject = _repository(tmp_path, monkeypatch, "s", (40, _pinned("beta.10")))
    _select(subject, _READ[1])
    installations = _installation(tmp_path).parent
    if case == "torn-records":
        for name in ("torn-1", "torn-2"):
            record = _installation(tmp_path) / "consumers" / name
            record.write_text("relative\n", encoding="utf-8")
    if case == "no-records":
        (installations / ("1" * 16)).mkdir()
        (installations / "install.lock").write_text("", encoding="utf-8")
    if case == "linked-installation":
        _installation(tmp_path).rename(tmp_path / "moved")
        (installations / ("0" * 16)).symlink_to(tmp_path / "moved", target_is_directory=True)
    if case == "linked-beside-its-target":
        (installations / ("1" * 16)).mkdir()
        (installations / ("2" * 16)).symlink_to(installations / ("1" * 16))
    if case == "dangling-link":
        (installations / ("1" * 16)).symlink_to(tmp_path / "gone")
    if case == "linked-file":
        # A link to a file is no installation, like a file that stands there itself.
        (tmp_path / "file").write_text("", encoding="utf-8")
        (installations / ("1" * 16)).symlink_to(tmp_path / "file")
    if case == "no-accepted-branch":
        git(subject, "branch", "-m", "dev", "trunk")
    if case == "torn-selection":
        selector = Path(git_common_dir(subject)) / "ethos/runtime/CURRENT"
        selector.write_text("torn\n", encoding="utf-8")
    release = {"VERSION": "0.2.0-beta.12\n", "CHANGELOG.md": CHANGELOG}
    product = _repository(tmp_path, monkeypatch, "product", (41, release))

    data = run_ethos("lane", "upgrade-from", "--root", product.as_posix(), "--json")["data"]

    rows = [(row["pinned"], row["current"]) for row in data["subjects"]]
    counted = ("unread", "unrecorded_installations", "subjects_with_unreadable_selection")
    assert (rows, tuple(data.get(name) for name in counted)) == UNREAD[case]


def _unlisted(tmp_path: Path) -> tuple[str, ...]:
    """The read of a product whose committed version has no changelog entry."""
    product = init_git_repo(tmp_path / "product")
    write_tree(product, {"VERSION": "0.2.0-beta.13\n", "CHANGELOG.md": CHANGELOG})
    commit_fixture(product, "chore: prepare the release")
    return ("lane", "upgrade-from", "--root", product.as_posix(), "--json")


def test_a_gap_outside_the_record_does_not_ask_for_the_record(tmp_path: Path) -> None:
    """Only a gap of the record names the record as its repair."""
    unlisted = run_ethos(*_unlisted(tmp_path))
    assert unlisted["required_gaps"] == ["release_changelog_target_missing:0.2.0-beta.13"]
    assert unlisted["next_action"].startswith("repair the reported gap")


_RAISED = [
    (
        PermissionError(errno.EACCES, "Permission denied", "/host/store"),
        ["release_upgrade_from_store_unreadable:EACCES"],
    ),
    (refusal(), ["OutcomeError"]),
]


@pytest.mark.parametrize(("raised", "gaps"), _RAISED, ids=["os-error", "refusal-without-a-gap"])
def test_an_error_of_the_read_blocks_and_names_itself_without_a_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raised: Exception, gaps: list[str]
) -> None:
    """An operating system error keeps its name and leaves its message, which holds a path.

    A refusal that carries no gap still blocks: it is named by its class.
    """

    def failed(*_args: object) -> dict[str, object]:
        raise raised

    monkeypatch.setattr(lane_repair, "upgrade_from_report", failed)
    refused = run_ethos(*_unlisted(tmp_path))
    assert (refused["verdict"], refused["required_gaps"]) == ("block", gaps)
    assert "/host/store" not in json.dumps(refused)


def test_a_refused_record_carries_every_gap_of_its_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The owner of a refusal's gaps reads the record's refusal, and keeps each gap.

    The record's reader names one gap today, so a stub stands for a reader that names two.
    """
    product = init_git_repo(tmp_path / "product")
    write_tree(product, {".ethos/release.toml": '[release]\nmirror = "independent"\n'})
    commit_fixture(product, "chore: declare the release")

    gaps = ["first_gap", "second_gap"]

    def refused(_config: object) -> None:
        raise refusal(*gaps)

    monkeypatch.setattr(predecessors, "recorded", refused)
    assert recorded_upgrade_from(product, git(product, "rev-parse", "HEAD")) == (None, gaps)


def test_a_host_without_a_store_derives_the_previous_release_alone(tmp_path: Path) -> None:
    """No recorded consumer is no subject: the release still upgrades from its predecessor."""
    product = init_git_repo(tmp_path / "product")
    write_tree(product, {"VERSION": "0.2.0-beta.12\n", "CHANGELOG.md": CHANGELOG})
    commit_fixture(product, "chore: prepare the release")
    data = run_ethos("lane", "upgrade-from", "--root", product.as_posix(), "--json")["data"]
    assert (data["derived"], data["subjects"]) == ({"0.2.0-beta.11": "attested-main"}, [])
    assert data["unread"] == 0
