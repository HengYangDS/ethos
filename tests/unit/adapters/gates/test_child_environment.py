"""A result states what its declared commands inherit: names, classes and counts, no value."""

from __future__ import annotations

import json
import os
import sys
from subprocess import CompletedProcess
from subprocess import TimeoutExpired
from unittest.mock import Mock
from unittest.mock import patch

import pytest

import ethos.adapters.gates.child_environment as child_environment
import ethos.adapters.gates.runner as gate_runner
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode

# Every variable of these launches holds this value, and no report may hold it.
VALUE = "never-reported"
# A launch's Git overlay: a plain key, a key whose subsection holds a URL, and text that is no key.
OVERLAY = {
    "GIT_CONFIG_KEY_0": "safe.directory",
    "GIT_CONFIG_KEY_1": "url.https://never-reported@host/.insteadOf",
    "GIT_CONFIG_KEY_2": VALUE,
    "GIT_CONFIG_VALUE_0": VALUE,
}


# Names that a marker classes `credential`, and names that only hold a fragment of a marker.
CLASSED = ("SECRET_KEY", "DJANGO_SECRET_KEY", "SECRET_KEY_BASE", "SSH_PRIVATE_KEY", "SIGNING_KEY")
CLASSED += ("COSIGN_PRIVATE_KEY", "ACCESS_KEY", "GPG_PASSPHRASE", "DOCKER_AUTH_CONFIG")
CLASSED += ("GITHUB_PAT", "GH_PAT")
UNCLASSED = ("MAX_TOKENS", "KEYBOARD_LAYOUT", "COMPASS_HOME", "PATH", "PASSWD_FILE")


@pytest.mark.parametrize("name", [*CLASSED, *UNCLASSED])
def test_a_name_is_classed_by_a_marker_and_never_by_a_fragment(tmp_path, name) -> None:
    """Each name alone in a launch: a marker classes it, a fragment of one classes nothing."""
    with patch.dict(os.environ, {name: VALUE}, clear=True):
        report = child_environment.inherited_environment(tmp_path, executed=True)["environment"]

    assert report["credential_classes"] == (["credential"] if name in CLASSED else [])


@pytest.mark.parametrize(
    ("names", "outside", "classes"),
    [
        (("SSH_AUTH_SOCK",), 1, ["ssh-agent"]),
        (("GH_TOKEN", "GITLAB_ACCESS_TOKEN"), 2, ["forge-token"]),
        (("AWS_SECRET_ACCESS_KEY", "AWS_REGION"), 2, ["cloud-credential"]),
        (("NPM_TOKEN", "MAX_TOKENS"), 2, ["credential"]),
        # A shell that activated Mise and holds a credential of every class.
        (
            ("__MISE_DIFF", "GH_TOKEN", "SSH_AUTH_SOCK", "AZURE_CLIENT_SECRET", "PGPASSWORD"),
            5,
            ["cloud-credential", "credential", "forge-token", "ssh-agent"],
        ),
        # The kept names with one further variable, and the kept names alone in any letter case.
        (("HOME", "PATH", "TMPDIR", "CHROME_BIN"), 1, []),
        (("home", "Path", "TMPDIR", "User", "LOGNAME"), 0, []),
    ],
)
def test_a_launch_is_measured_against_the_list(tmp_path, names, outside, classes) -> None:
    """The first, sixth and seventh measured cases as reports: a launch states its distance."""
    with patch.dict(os.environ, dict.fromkeys(names, VALUE), clear=True):
        report = child_environment.inherited_environment(tmp_path, executed=True)

    assert report["environment"] == {
        "mode": "inherited",
        "names": len(names),
        "outside_allow_list": outside,
        "credential_classes": classes,
        "locked_toolchain": "undeclared",
        "outside_lock": [],
        "git_overlay_keys": [],
    }


@pytest.mark.parametrize(
    ("read", "state", "outside"),
    [
        (
            (("mise_executable_outside_tool:uv",), {}),
            "declared",
            ["mise_executable_outside_tool:uv"],
        ),
        (
            ValueError("mise_supply_unavailable:ls:never-reported"),
            "unread:mise_supply_unavailable",
            [],
        ),
        (OSError(VALUE), "unread:OSError", []),
        # Python 3.12 resolves a symlink loop with this class.
        (RuntimeError(VALUE), "unread:RuntimeError", []),
    ],
)
def test_a_lock_is_read_or_named_unread_and_an_overlay_names_its_keys(
    monkeypatch, tmp_path, read, state, outside
) -> None:
    """An unread lock is a state of the report, and a Git key keeps only its two names."""
    monkeypatch.setattr(child_environment, "repository_mise_files", lambda _root: {})
    monkeypatch.setattr(child_environment, "launch_supply", Mock(side_effect=[read]))

    with patch.dict(os.environ, OVERLAY, clear=True):
        report = child_environment.inherited_environment(tmp_path, executed=True)["environment"]

    assert (report["locked_toolchain"], report["outside_lock"]) == (state, outside)
    assert report["git_overlay_keys"] == ["safe.directory", "unreadable", "url.insteadOf"]
    assert VALUE not in str(report)


@pytest.mark.parametrize(
    ("word", "found", "supplier"),
    [
        ("absent", None, "unresolved"),
        ("uv", "installs/uv/bin/uv", "locked"),
        # The gaps' ownership rule: Node's bundled npm is not the locked npm, its npx is Node's.
        ("npm", "installs/node/bin/npm", "launch-path"),
        ("npx", "installs/node/bin/npx", "locked"),
        ("git", "host/git", "host-baseline"),
    ],
)
def test_a_first_word_names_what_supplied_it(monkeypatch, tmp_path, word, found, supplier) -> None:
    """Four of the five suppliers from one read lock; the runner's test below names a declared."""
    host = Mock(return_value=(str(tmp_path / "host"),))
    monkeypatch.setattr(child_environment, "host_command_baseline", host)
    started = str(tmp_path / found) if found else None
    rows = {}
    for tool in ("uv", "node", "npm"):
        (tmp_path / "installs" / tool).mkdir(parents=True)
        rows[tool] = [{"installed": True, "install_path": str(tmp_path / "installs" / tool)}]
    listed = CompletedProcess((), 0, json.dumps(rows), "")
    monkeypatch.setattr("ethos.adapters.toolchain.mise.run_mise", Mock(return_value=listed))
    monkeypatch.setattr(child_environment, "repository_mise_files", lambda _root: {})

    state, _gaps, lock = child_environment.locked_toolchain(tmp_path)
    origin = child_environment.command_origin(word, started, lock)

    assert (state, origin) == ("declared", {"executable": started or "", "supplier": supplier})


@pytest.mark.parametrize(
    ("word", "launches", "supplier"),
    [
        ("tool", ("first", "second"), "launch-path"),
        ("tools/tool", ("",), "declared"),
        (sys.executable, ("",), "declared"),
    ],
)
def test_one_command_passes_from_two_launches_and_names_two_executables(
    monkeypatch, tmp_path, word, launches, supplier
) -> None:
    """The third measured case: the verdict is the same, and the result says what was started.

    A bare name follows its launch; a repository path and the bound interpreter are declared.
    """
    gate = Gate(id="check", kind="lint", command=(word,))
    node = PlanNode(id="check", kind="check", command=gate_runner.gate_execution_identity(gate))
    ran = Mock(return_value=(CompletedProcess((word,), 0, "", ""), None))
    monkeypatch.setattr(gate_runner, "gate_attempt", ran)
    started = [str(tmp_path / launch / word) for launch in launches]
    monkeypatch.setattr(gate_runner.shutil, "which", Mock(side_effect=started))

    results = [gate_runner.LocalGateRunner().run(node, gate, root=tmp_path) for _ in launches]

    assert [(result.verdict, result.executable, result.supplier) for result in results] == [
        ("pass", path, supplier) for path in started
    ]


@pytest.mark.parametrize(("word", "reads"), [("tool", 1), ("tools/tool", 0)])
def test_a_lock_read_takes_no_time_from_a_command_and_a_path_needs_none(
    monkeypatch, tmp_path, word, reads
) -> None:
    """A slow read of the lock is outside the deadline, runs once a runner, and never for a path."""
    gate = Gate(id="check", kind="lint", command=(word,))
    node = PlanNode(id="check", kind="check", command=gate_runner.gate_execution_identity(gate))
    ran = Mock(return_value=(CompletedProcess((word,), 0, "", ""), None))
    monkeypatch.setattr(gate_runner, "gate_attempt", ran)
    monkeypatch.setattr(gate_runner.shutil, "which", Mock(return_value=str(tmp_path / word)))
    clock = Mock(return_value=0.0)
    monkeypatch.setattr(gate_runner, "monotonic", clock)
    read = ("undeclared", (), {})
    slow = Mock(side_effect=lambda _root: setattr(clock, "return_value", 1000.0) or read)
    monkeypatch.setattr(gate_runner, "locked_toolchain", slow)
    runner = gate_runner.LocalGateRunner()

    results = [runner.run(node, gate, root=tmp_path) for _ in range(2)]

    assert [result.verdict for result in results] == ["pass", "pass"]
    assert ran.call_args_list[0].kwargs["timeout"] == gate_runner.gate_timeout(gate)[0]
    assert slow.call_count == reads


@pytest.mark.parametrize(
    ("outcome", "exit_code", "supplier"),
    [
        ("timed-out", 124, "launch-path"),
        ("missing", 127, "launch-path"),
        ("absent", 127, "unresolved"),
    ],
)
def test_a_command_that_did_not_finish_still_names_what_it_started(
    monkeypatch, tmp_path, outcome, exit_code, supplier
) -> None:
    """A declared command that timed out, or that is not there, names its origin like any other.

    A name that the launch path resolved and that could not start names its path; a name that no
    launch path holds names no executable and is unresolved.
    """
    gate = Gate(id="check", kind="lint", command=("ethos-test-tool-on-no-launch-path",))
    node = PlanNode(id="check", kind="check", command=gate_runner.gate_execution_identity(gate))
    started = "" if outcome == "absent" else str(tmp_path / "launch" / "tool")
    monkeypatch.setattr(gate_runner.shutil, "which", Mock(return_value=started or None))
    if outcome == "timed-out":
        monkeypatch.setattr(
            gate_runner, "gate_attempt", Mock(side_effect=TimeoutExpired(gate.command, 1))
        )

    result = gate_runner.LocalGateRunner().run(node, gate, root=tmp_path)

    assert (result.verdict, result.exit_code) == ("unknown", exit_code)
    assert (result.executable, result.supplier) == (started, supplier)
