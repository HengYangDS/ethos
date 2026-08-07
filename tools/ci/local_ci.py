"""Cross-platform local CI owner for the single locked project runtime."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import current_tracked_head

if TYPE_CHECKING:
    import nox

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "build/evidence/local-ci/fallback.json"
COMMAND = "uv run --frozen --offline python -m nox -s local_ci"
VERIFY_SESSIONS = (
    "lint",
    "schemas",
    "import_boundaries",
    "dependencies",
    "docstrings",
    "module_layout",
    "product_boundary",
    "vulnerabilities",
    "ci_templates",
    "format_selection",
    "architecture_projection",
    "runbook_registry",
    "repository_hygiene",
    "prose",
    "shell_lint",
    "markdown_lint",
    "config_quality",
    "hosted_observation",
)
PARALLEL_SESSIONS = (
    "lint",
    "schemas",
    "import_boundaries",
    "dependencies",
    "vulnerabilities",
    "ci_templates",
    "format_selection",
    "architecture_projection",
    "runbook_registry",
    "repository_hygiene",
    "prose",
    "shell_lint",
    "markdown_lint",
    "config_quality",
    "hosted_observation",
)
SERIAL_PROOF_SESSIONS = ("docstrings", "module_layout", "product_boundary")
PLATFORM_ADAPTERS = ("tools/ci/scripts/run-secrets-scan.sh",)
PREPARE_SESSIONS = ("prepare_install_supply",)
DELIVERY_SESSIONS = ("build", "install_smoke", "supply_chain")


def owner_commands() -> list[str]:
    """Return the exact local verification closure in execution order."""
    sessions = (*VERIFY_SESSIONS, "tests", *PREPARE_SESSIONS, *DELIVERY_SESSIONS)
    return [
        *(f"uv run --frozen --offline python -m nox -s {name}" for name in sessions),
        *PLATFORM_ADAPTERS,
    ]


def _run_session(session: nox.Session, name: str) -> None:
    session.run(sys.executable, "-m", "nox", "-s", name, env={"PYTHONWARNINGS": "error"})


def _run_parallel_sessions(session: nox.Session) -> None:
    """Run independent read-only owners concurrently with bounded output."""
    log_root = ROOT / "build/runtime/logs/local-ci"
    log_root.mkdir(parents=True, exist_ok=True)

    def run(name: str) -> tuple[str, int, str]:
        completed = subprocess.run(
            (sys.executable, "-m", "nox", "-s", name),
            cwd=ROOT,
            env=os.environ | {"PYTHONWARNINGS": "error"},
            text=True,
            capture_output=True,
            check=False,
        )
        output = f"{completed.stdout}{completed.stderr}"
        (log_root / f"{name}.log").write_text(output, encoding="utf-8")
        return name, completed.returncode, output[-4000:]

    failures = []
    workers = min(4, len(PARALLEL_SESSIONS))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run, name): name for name in PARALLEL_SESSIONS}
        for future in as_completed(futures):
            name, returncode, tail = future.result()
            session.log(f"{name}: {'pass' if returncode == 0 else 'fail'}")
            if returncode:
                failures.append(f"{name}:\n{tail}")
    if failures:
        session.error("parallel local CI owners failed:\n" + "\n".join(failures))


def run(session: nox.Session) -> None:
    """Run the complete local closure and write one exact-HEAD evidence envelope."""
    head = current_tracked_head(ROOT)
    _run_parallel_sessions(session)
    for name in SERIAL_PROOF_SESSIONS:
        _run_session(session, name)
    for relative in PLATFORM_ADAPTERS:
        session.run(str(ROOT / relative), env={"PYTHONWARNINGS": "error"})
    _run_session(session, "tests")
    for name in PREPARE_SESSIONS:
        _run_session(session, name)
    for name in DELIVERY_SESSIONS:
        _run_session(session, name)
    observed = current_tracked_head(ROOT)
    if observed != head:
        session.error(f"local CI HEAD moved: {head} -> {observed}")
    payload = {
        "schema_version": 1,
        "kind": "ethos_local_ci_fallback_evidence",
        "verdict": "pass",
        "state": "passed",
        "head": head,
        "command": COMMAND,
        "owner_commands": owner_commands(),
        "generated_at": datetime.now(UTC).isoformat(),
        "head_stability": "verified_before_evidence_write",
        "hosted_ci_status_claimed": False,
        "remote_publication_claimed": False,
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    EVIDENCE.write_text(rendered, encoding="utf-8")
    session.log(rendered)
