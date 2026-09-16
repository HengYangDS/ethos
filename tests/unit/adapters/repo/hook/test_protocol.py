"""Native hook protocol must not initialize unused authority or command dispatch."""

from __future__ import annotations

import json
import subprocess
import sys
from io import StringIO
from types import MappingProxyType
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.hook.admission as hook_admission
from ethos.adapters.repo.hook.protocol import execute_hook
from tests.support.runtime_scenarios import REPOSITORY_ROOT

if TYPE_CHECKING:
    from pathlib import Path

_PROTOCOL_PROBE = """
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])

class UnusedAuthority:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'cyclopts', 'pydantic'} or fullname.startswith(
            ('ethos.adapters.admission', 'ethos.adapters.repo.runtime.selection')
        ):
            raise ImportError('unused authority initialized: ' + fullname)

sys.meta_path.insert(0, UnusedAuthority())
from ethos.adapters.repo.hook.protocol import execute_hook
raise SystemExit(execute_hook(Path.cwd(), sys.argv[2], tuple(sys.argv[3:]), stdin=sys.stdin))
"""


def _protocol(root: Path, phase: str, body: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "-I",
            "-c",
            _PROTOCOL_PROBE,
            str(REPOSITORY_ROOT / "src"),
            "reference-transaction",
            phase,
        ],
        cwd=root,
        input=body,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


@pytest.mark.parametrize(
    ("phase", "body"),
    [
        ("committed", f"{'a' * 40} {'b' * 40} refs/heads/dev\n"),
        ("aborted", f"{'a' * 40} {'b' * 40} refs/heads/dev\n"),
        ("prepared", f"{'a' * 40} {'b' * 40} refs/ethos/attestations-set\n"),
        ("prepared", f"{'a' * 40} {'b' * 40} refs/tags/v1\n"),
        ("prepared", f"{'a' * 40} {'a' * 40} refs/heads/dev\n"),
        ("prepared", ""),
    ],
)
def test_unused_admission_cannot_become_a_notification_dependency(
    tmp_path: Path, phase: str, body: str
) -> None:
    """Eager CLI or policy initialization breaks a valid no-admission protocol."""
    result = _protocol(tmp_path, phase, body)
    assert result.returncode == 0, result.stderr
    assert result.stdout == result.stderr == ""


@pytest.mark.parametrize("phase", ["prepared", "committed", "aborted"])
def test_malformed_protocol_fails_before_initializing_authority(tmp_path: Path, phase: str) -> None:
    """A malformed envelope is rejected by its owner, not hidden by heavy startup."""
    result = _protocol(tmp_path, phase, "malformed\n")
    assert result.returncode == 1
    assert json.loads(result.stderr)["required_gaps"] == ["ref_update_invalid"]


@pytest.mark.parametrize(
    ("arguments", "body", "expected_gap"),
    [
        (("reference-transaction", "committed"), "", ""),
        (("reference-transaction", "prepared"), "malformed\n", "ref_update_invalid"),
        (("unknown",), "", "hook_name_invalid"),
        ((), "", "hook_name_invalid"),
    ],
)
def test_native_entrypoint_preserves_protocol_without_command_dispatch(
    tmp_path: Path, arguments: tuple[str, ...], body: str, expected_gap: str
) -> None:
    """The installed module consumes native argv and stdin without CLI loading."""
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True, timeout=10)
    probe = _PROTOCOL_PROBE.split("from ethos.adapters.repo.hook.protocol import", maxsplit=1)[0]
    probe += (
        "import runpy\n"
        "sys.argv = ['native-hook', *sys.argv[2:]]\n"
        "runpy.run_module('ethos.adapters.repo.hook.protocol', run_name='__main__')\n"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-I", "-c", probe, str(REPOSITORY_ROOT / "src"), *arguments],
        cwd=tmp_path,
        input=body,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == int(bool(expected_gap)), result.stderr
    if expected_gap:
        assert json.loads(result.stderr)["required_gaps"] == [expected_gap]
    else:
        assert result.stdout == result.stderr == ""


def test_prepared_branch_cannot_use_the_notification_path(tmp_path: Path) -> None:
    """Missing admission code rejects an actual prepared update, never passing it."""
    result = _protocol(tmp_path, "prepared", f"{'a' * 40} {'b' * 40} refs/heads/work/change\n")
    assert result.returncode == 1
    assert json.loads(result.stderr)["required_gaps"] == [
        "unused authority initialized: ethos.adapters.admission"
    ]


def test_native_entrypoint_rejects_an_unavailable_repository(tmp_path: Path) -> None:
    """A missing Git root remains a failed native result rather than a traceback."""
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "ethos.adapters.repo.hook.protocol",
            "reference-transaction",
            "prepared",
        ],
        cwd=tmp_path,
        input="",
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 1
    failure = json.loads(result.stderr)
    assert failure["hook"] == "reference-transaction"
    assert failure["verdict"] == "block"
    assert failure["required_gaps"]


@pytest.mark.parametrize("verdict", ["pass", "block", "unknown"])
def test_hook_projects_nested_immutable_evidence_without_changing_the_verdict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    verdict: str,
) -> None:
    """A transport projects immutable proof data; it does not decide admission."""
    commitment = MappingProxyType(
        {"schema_version": 3, "id": "change:publication", "acceptance": ("exact signed source",)}
    )
    report = {
        "verdict": verdict,
        "required_gaps": () if verdict == "pass" else ("accepted_closeout_effect_not_attested",),
        "proof_admission": MappingProxyType({"attestation": {"commitment": commitment}}),
        "next_action": "ethos land --json",
    }
    monkeypatch.setattr(hook_admission, "admit_hook", lambda *_args, **_kwargs: (report,))
    result = execute_hook(tmp_path, "pre-push", ("origin",), stdin=StringIO())
    captured = capsys.readouterr()
    assert result == int(verdict != "pass")
    assert captured.out == ""
    if verdict == "pass":
        assert captured.err == ""
    else:
        observed = json.loads(captured.err)
        assert observed["verdict"] == verdict
        assert observed["required_gaps"] == ["accepted_closeout_effect_not_attested"]
        assert observed["next_action"] == "ethos land --json"
        assert observed["proof_admission"]["attestation"]["commitment"] == {
            "schema_version": 3,
            "id": "change:publication",
            "acceptance": ["exact signed source"],
        }
    assert report["proof_admission"]["attestation"]["commitment"] is commitment


@pytest.mark.parametrize("invalid", [object(), float("nan"), {"unserializable"}])
def test_hook_serialization_failure_is_a_machine_readable_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    invalid: object,
) -> None:
    """Unexpected evidence values never escape the hook as a Python traceback."""
    report = {"verdict": "block", "required_gaps": ["original_gap"], "evidence": invalid}
    monkeypatch.setattr(hook_admission, "admit_hook", lambda *_args, **_kwargs: (report,))
    assert execute_hook(tmp_path, "pre-push", ("origin",), stdin=StringIO()) == 1
    result = json.loads(capsys.readouterr().err)
    assert result["verdict"] == "block"
    assert result["required_gaps"] == ["hook_report_not_json_native"]


def test_pre_push_evaluates_every_update_and_blocks_the_batch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(hook_admission, "current_runtime", lambda _common: None)

    def admit(**kwargs: object) -> dict[str, object]:
        calls.append(kwargs)
        blocked = kwargs["target_ref"] == "refs/heads/rejected"
        return {
            "verdict": "block" if blocked else "pass",
            "state": "blocked" if blocked else "admitted",
            "required_gaps": ["commit_subject_invalid:rejected"] if blocked else [],
        }

    monkeypatch.setattr(hook_admission, "push_admission_report", admit)
    zero = "0" * 40
    updates = "".join(
        (
            f"refs/heads/first {'a' * 40} refs/heads/first {'1' * 40}\n",
            f"refs/heads/deleted {zero} refs/heads/deleted {'2' * 40}\n",
            f"refs/heads/rejected {'b' * 40} refs/heads/rejected {'3' * 40}\n",
            f"refs/tags/v1 {'c' * 40} refs/tags/v1 {'4' * 40}\n",
        )
    )

    result = execute_hook(tmp_path, "pre-push", ("gitlab",), stdin=StringIO(updates))

    assert result == 1
    assert [(call["target_ref"], call["remote_head"], call["remote_name"]) for call in calls] == [
        ("refs/heads/first", "1" * 40, "gitlab"),
        ("refs/heads/deleted", "2" * 40, "gitlab"),
        ("refs/heads/rejected", "3" * 40, "gitlab"),
        ("refs/tags/v1", "4" * 40, "gitlab"),
    ]
    assert all("reconciliation" not in call for call in calls)
    assert json.loads(capsys.readouterr().err)["required_gaps"] == [
        "commit_subject_invalid:rejected"
    ]
