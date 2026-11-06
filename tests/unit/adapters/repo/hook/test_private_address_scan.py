"""ETHOS's content scans refuse private-class addresses by structure and never read history."""

from __future__ import annotations

import json
import shutil
import subprocess
import tomllib
from io import StringIO
from pathlib import Path

import pytest
from pydantic import ValidationError

import ethos.adapters.repo.hook.admission as hook_runtime
import tools.ci.toolchain.native as native_owner
from ethos.adapters.process import run_command
from ethos.adapters.repo.hook.protocol import execute_hook
from ethos.contracts.paradigm.declaration import RepositoryParadigm
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from tests.support.private_addresses import DOCUMENTATION_FORGE
from tests.support.private_addresses import DOCUMENTATION_TEXTS
from tests.support.private_addresses import PRIVATE_FORGE
from tests.support.private_addresses import PRIVATE_TEXTS
from tests.support.runtime_scenarios import REPOSITORY_ROOT
from tests.support.runtime_scenarios import git_process
from tools.ci import sessions

CONFIG = REPOSITORY_ROOT / ".config/checks/gitleaks/gitleaks.toml"
PARADIGM = REPOSITORY_ROOT / "src/ethos/contracts/paradigm/paradigm.toml"


def _gitleaks() -> str:
    executable = shutil.which("gitleaks")
    assert executable is not None, "the declared secrets gate requires native gitleaks"
    return executable


def _flagged_lines(text: str) -> set[int]:
    """Return the input lines that ETHOS's configured rule reports, without echoing them."""
    result = run_command(
        REPOSITORY_ROOT,
        (
            _gitleaks(),
            "stdin",
            "--config",
            str(CONFIG),
            "--redact=100",
            "--no-banner",
            "--timeout=20",
            "--report-format=json",
            "--report-path=-",
        ),
        stdin=text + "\n",
        timeout=30,
        remove_env_prefixes=("GITLEAKS_",),
    )
    findings = json.loads(result.stdout)
    assert result.returncode == (1 if findings else 0)
    return {item["StartLine"] for item in findings if item["RuleID"] == "private-network-address"}


def _stage(repo: Path, relative: str, text: str) -> None:
    (repo / relative).parent.mkdir(parents=True, exist_ok=True)
    (repo / relative).write_text(text, encoding="utf-8")
    assert git_process(repo, "add", relative).returncode == 0


def _commit(repo: Path, message: str) -> None:
    """Record fixture history without signing, hooks or ambient identity."""
    identity = ("-c", "user.name=ETHOS Fixture", "-c", "user.email=fixture@example.invalid")
    options = ("-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null")
    command = ("commit", "--no-verify", "--quiet", "-m", message)
    assert git_process(repo, *identity, *options, *command).returncode == 0


def test_content_rule_carries_the_paradigm_pattern() -> None:
    """One declared pattern: the Gitleaks rule is the paradigm's string, byte for byte."""
    rules = tomllib.loads(CONFIG.read_text(encoding="utf-8"))["rules"]
    [rule] = [rule for rule in rules if rule["id"] == "private-network-address"]
    paradigm = load_repository_paradigm()
    assert rule["regex"] == paradigm.private_address
    assert not paradigm.names_private_address(CONFIG.read_text(encoding="utf-8"))
    assert not paradigm.names_private_address(PARADIGM.read_text(encoding="utf-8"))


def test_an_uncompilable_pattern_never_loads() -> None:
    """The paradigm refuses a private-address pattern that does not compile."""
    payload = tomllib.loads(PARADIGM.read_text(encoding="utf-8"))
    payload["private_address"] = "[a-z"
    with pytest.raises(ValidationError, match="private address pattern does not compile"):
        RepositoryParadigm.model_validate(payload)


@pytest.mark.parametrize(
    ("name", "found"),
    [*((name, True) for name in PRIVATE_TEXTS), *((name, False) for name in DOCUMENTATION_TEXTS)],
)
def test_message_admission_reads_classes_not_names(name: str, *, found: bool) -> None:
    """Private classes match; documentation forms, the public identity and markers do not."""
    text = {**PRIVATE_TEXTS, **DOCUMENTATION_TEXTS}[name]
    assert load_repository_paradigm().names_private_address(text) is found


def test_native_scan_gives_the_same_verdict_per_line() -> None:
    """Gitleaks reports every private line and no documentation line, as Python does."""
    private = list(PRIVATE_TEXTS.values())
    assert _flagged_lines("\n".join(private)) == set(range(1, len(private) + 1))
    assert _flagged_lines("\n".join(DOCUMENTATION_TEXTS.values())) == set()


def test_history_alone_fails_neither_content_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The staged and tracked scans pass a repository whose history alone names an address."""
    repo = tmp_path
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    monkeypatch.setattr(hook_runtime, "current_runtime", lambda _common: None)
    monkeypatch.setattr(
        "ethos.adapters.admission.prewrite.prewrite_guard", lambda **_kwargs: {"verdict": "pass"}
    )
    _stage(repo, CONFIG.relative_to(REPOSITORY_ROOT).as_posix(), CONFIG.read_text(encoding="utf-8"))
    for remote in (PRIVATE_FORGE, DOCUMENTATION_FORGE):
        _stage(repo, "peer.txt", f"remote http://{remote}/team/repo\n")
        _commit(repo, "chore: record the peer")
    exits = []
    for line in ("at forge.example.invalid", f"at http://{PRIVATE_FORGE}"):
        _stage(repo, "notes.txt", f"mirrored {line}\n")
        exits.append(execute_hook(repo, "pre-commit", (), stdin=StringIO()))
    assert exits == [0, 1]
    assert "staged_secret_scan_failed" in capsys.readouterr().err
    assert git_process(repo, "reset", "--quiet", "--hard").returncode == 0
    supply = Path(_gitleaks()).parent
    monkeypatch.setattr(native_owner, "supply_tool", lambda _root, _name: supply)
    monkeypatch.setattr(sessions, "ROOT", repo)
    outcomes: list[int] = []

    def run(_session: object, *args: str) -> None:
        outcomes.append(subprocess.run(args, capture_output=True, check=False).returncode)

    sessions.secrets(type("Session", (), {"run": run, "error": pytest.fail})())
    history = run_command(
        repo,
        (_gitleaks(), "git", "--config", str(CONFIG), "--redact=100", "--no-banner", str(repo)),
        timeout=60,
        remove_env_prefixes=("GITLEAKS_",),
    )
    assert (outcomes, history.returncode) == ([0], 1)
