"""Public source-purpose journeys use audit/quality doubles and real Git effects."""

from __future__ import annotations

import hashlib
import json
import platform
import tomllib
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from subprocess import CompletedProcess

import tomli_w

import tests
from ethos.adapters.mutation.proof_admission import proof_attestation
from ethos.adapters.mutation.proof_artifacts import artifact_checks
from ethos.adapters.mutation.proof_artifacts import proof_artifact_root
from ethos.adapters.repo.dependency_acceptance import product_audit_snapshot
from ethos.adapters.repo.gate_policy import observe_quality_subjects
from ethos.adapters.repo.runtime.authority import invoking_build_identity
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.contracts.semantic import Attestation
from ethos.repository.policy.quality.dependency_acceptance import AUDIT_INPUTS
from ethos.repository.policy.quality.dependency_acceptance import AUDIT_POLICY_PATH
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import WorkLaneFixture
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import create_change_source_lane
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_candidate
from tests.support.runtime_scenarios import create_fixture_python
from tests.support.runtime_scenarios import install_fixture_hook_runtime

AUDIT = "dependency-vulnerabilities"
PARSER = "postcss-selector-parser"
NODE = f"node_modules/npm/node_modules/{PARSER}"
ADVISORY = "https://github.com/advisories/GHSA-rj75-hqrm-r3gf"
FIXTURE_INTEGRITY = "sha512-Zml4dHVyZQ=="
COMMAND = ("python", "-m", "nox", "-s", "vulnerabilities", "--", "--scope", "local-development")
EXPIRED = "proof_dependency_acceptance:unapproved_or_expired_findings"


def _declare_audit(root: Path, expires: datetime) -> None:
    path = root / "system/gates.toml"
    declaration = tomllib.loads(path.read_text())
    native = load_gate_registry_declaration().registry()[AUDIT]
    declaration["gates"].append(native.model_dump(mode="json", exclude_none=True))
    for floor in ("default", "full"):
        declaration["proof_sets"][floor].append(AUDIT)
    path.write_text(tomli_w.dumps(declaration), encoding="utf-8")
    manifest = {
        "name": "fixture",
        "version": "0.0.0",
        "private": True,
        "devDependencies": {"npm": "12.2.0"},
    }
    lock = {
        "lockfileVersion": 3,
        "packages": {
            "": manifest,
            "node_modules/npm": {"version": "12.2.0", "integrity": FIXTURE_INTEGRITY},
            NODE: {"version": "7.1.4", "inBundle": True},
        },
    }
    materials = {
        "package.json": json.dumps(manifest),
        "package-lock.json": json.dumps(lock),
        "pyproject.toml": "[project]\nname='fixture'\nversion='0.0.0'\nrequires-python='>=3.12'\n",
        "uv.lock": "version = 1\nrequires-python = '>=3.12'\npackage = []\n",
    }
    source_root = Path(tests.__file__).resolve().parent.parent
    for name in (*AUDIT_INPUTS[5:], "noxfile.py"):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((source_root / name).read_bytes())
    for name, content in materials.items():
        (root / name).write_text(content + "\n", encoding="utf-8")
    policy = root / AUDIT_POLICY_PATH
    policy.parent.mkdir(parents=True, exist_ok=True)
    policy.write_text(
        tomli_w.dumps(
            {
                "owner": "fixture:security",
                "summary": "Native audit fixture",
                "runner": "nox -s vulnerabilities",
                "timeout_seconds": 120,
                "dispositions": [
                    {
                        "ecosystem": "npm",
                        "advisory_url": ADVISORY,
                        "package": PARSER,
                        "version": "7.1.4",
                        "integrity": FIXTURE_INTEGRITY,
                        "nodes": [NODE],
                        "lock_sha256": hashlib.sha256(
                            (root / "package-lock.json").read_bytes()
                        ).hexdigest(),
                        "scope": "local-development",
                        "host": platform.node(),
                        "owner": "fixture:owner",
                        "approval_ref": "fixture:local-parser-only",
                        "rationale": "Isolated local-source fixture; no downstream authority.",
                        "expires_at": expires,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    ignore = root / ".gitignore"
    ignore.write_text(ignore.read_text() + "\nbuild/\n.venv/\n", encoding="utf-8")


def native_result(root: Path, command) -> CompletedProcess[str]:
    python = {
        "summary": {"audited_packages": 1, "vulnerabilities": 0, "adverse_statuses": 0},
        "vulnerabilities": [],
        "adverse_statuses": [],
    }
    npm = {
        "auditReportVersion": 2,
        "vulnerabilities": {
            PARSER: {
                "name": PARSER,
                "severity": "moderate",
                "nodes": [NODE],
                "via": [{"name": PARSER, "dependency": PARSER, "url": ADVISORY, "range": "<7.1.6"}],
            },
            "npm": {
                "name": "npm",
                "severity": "moderate",
                "nodes": ["node_modules/npm"],
                "via": [PARSER],
            },
        },
        "metadata": {
            "vulnerabilities": {
                "info": 0,
                "low": 0,
                "moderate": 2,
                "high": 0,
                "critical": 0,
                "total": 2,
            },
            "dependencies": {"total": 3},
        },
    }
    payload = {
        "command": "dependency-audit",
        "product_policy": product_audit_snapshot(build=invoking_build_identity())[1],
        "head": git(root, "rev-parse", "HEAD"),
        "generated_at": datetime.now(UTC).isoformat(),
        "state": "finished",
        "verdict": "block",
        "inputs": {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in AUDIT_INPUTS
        },
        "required_gaps": ["npm:vulnerabilities_or_adverse_statuses"],
        "checks": [
            {
                "ecosystem": "python",
                "command": ["uv", "audit", "--frozen"],
                "exit_code": 0,
                "verdict": "pass",
                "reason": "clean",
                "stdout": json.dumps(python),
                "stderr": "",
            },
            {
                "ecosystem": "npm",
                "command": ["node", "npm-cli.js", "audit", "--json"],
                "exit_code": 1,
                "verdict": "block",
                "reason": "vulnerabilities_or_adverse_statuses",
                "stdout": json.dumps(npm),
                "stderr": "",
            },
        ],
        "decision": {
            "scope": "local-development",
            "verdict": "pass",
            "reason": "authorized_findings",
        },
    }
    return CompletedProcess(command, 0, json.dumps(payload), "")


def quality_report(root: Path, *, axis: str) -> dict:
    """Double the separate quality-tool boundary, not proof admission or Git."""
    tree, subjects = observe_quality_subjects(root)
    paths = [
        subject.path for subject in subjects if axis != "behavior" or subject.requires_behavior
    ]
    return {
        "verdict": "pass",
        "quality_evidence": {"axis": axis, "source_tree": tree, "selected_paths": paths},
    }


def prepare_source(
    tmp_path: Path, actor: str, *, native_scan: bool | None = None
) -> tuple[WorkLaneFixture, str, str]:
    repo, candidate = start_adopted_candidate(tmp_path, release_mirror="accepted_ff")
    roles = load_branch_role_policy(repo)
    registry = repo / "system/gates.toml"
    gates = tomllib.loads(registry.read_text())
    for identity, kind, provider in (
        ("behavior", "test", "behavior"),
        ("static", "lint", "static"),
    ):
        gates["gates"].append(
            {
                "id": identity,
                "kind": kind,
                "providers": [f"ethos.adapters.gates.code_quality:{provider}_report"],
                "execution_mode": "provider",
                "profile": "repository",
                "tool_adapter": "ethos",
                "evidence_class": "proof",
                "trust_bearing": True,
            }
        )
        for floor in ("default", "full"):
            gates["proof_sets"][floor].append(identity)
    registry.write_text(tomli_w.dumps(gates), encoding="utf-8")
    if native_scan is None:
        _declare_audit(repo, datetime.now(UTC) + timedelta(hours=1))
    else:
        native = {
            "id": "native-dependencies",
            "kind": "static",
            "command": ["git", "grep", "-q", "^module ", "HEAD", "--", "go.mod"],
            "evidence_class": "proof",
            "trust_bearing": True,
        }
        selected = [gate for gate in gates["gates"] if gate["id"] in {"behavior", "static"}]
        selected.append(native)
        selected[1]["depends_on"] = [native["id"]]
        profile = repo / ".ethos/profile.toml"
        declaration = tomllib.loads(profile.read_text())
        declaration["proof"] = {
            "code_correctness_gates": [gate["id"] for gate in selected],
            "code_correctness_map": {"behavior": "behavior", "static-analysis": "static"},
            "gates": selected,
        }
        profile.write_text(tomli_w.dumps(declaration), encoding="utf-8")
        (repo / "go.mod").write_text(
            "module example.test/native\n" if native_scan else "invalid native manifest\n",
            encoding="utf-8",
        )
        (repo / "cmd/native").mkdir(parents=True)
        (repo / "cmd/native/main.go").write_text(
            "package main\n\nfunc main() {}\n", encoding="utf-8"
        )
        ignore = repo / ".gitignore"
        ignore.write_text(ignore.read_text() + "\nbuild/\n.venv/\n", encoding="utf-8")
    before = commit_fixture(repo, "test: native audit declaration")
    git(candidate, "reset", "--hard", before)
    git(repo, "branch", roles.release_branch, before)
    git(repo, "worktree", "add", (tmp_path / "repo-release").as_posix(), roles.release_branch)
    assert install_fixture_hook_runtime(repo)["current"]
    work = create_change_source_lane(
        repo,
        tmp_path / "repo-work-source",
        branch=roles.work_branch("source"),
        holder_ref=actor,
        base_ref=roles.candidate_branch,
    )
    create_fixture_python(work / ".venv")
    commit_fixture_file(work, "README.md", "# Local source candidate\n", "test: source")
    tasks = work / "openspec/changes/fixture-change/tasks.md"
    head = commit_fixture_file(
        work,
        tasks.relative_to(work).as_posix(),
        tasks.read_text().replace("[ ]", "[x]"),
        "test: completed progress",
    )
    return WorkLaneFixture(repo, candidate, work), before, head


def prove_source(work: Path, head: str, stdout_attempts: list[str]) -> Attestation:
    proved = run_ethos(
        "prove",
        "--full",
        "--execute",
        "--expect-head",
        head,
        "--acceptance-purpose",
        "local-source",
        "--json",
        cwd=work,
    )
    proof = Attestation.model_validate(proved["data"]["attestation"])
    assert proof.subject == f"git:commit:{head}"
    assert proof.payload.body["plan"]["policy"]["acceptance_purpose"] == "local-source"
    store = proof_artifact_root(work)
    checks, gaps = artifact_checks(store, proof)
    assert not gaps
    assert checks is not None
    declared = load_gate_registry_declaration(work / "system/gates.toml")
    assert {check["action_id"] for check in checks} == set(declared.proof_sets.full)
    audit = next(check for check in checks if check["action_id"] == AUDIT)
    assert stdout_attempts[-1] == audit["stdout"]
    raw = json.loads(audit["stdout"])
    assert raw["head"] == head
    assert raw["verdict"] == "block"
    assert audit["verdict"] == "pass"
    assert raw["checks"][1]["exit_code"] == 1
    selected, gaps = proof_attestation(
        work,
        head,
        store=store,
        attestation_id=proof.id,
        acceptance_purpose="local-source",
    )
    assert not gaps
    assert selected is not None
    assert selected.id == proof.id
    return proof
