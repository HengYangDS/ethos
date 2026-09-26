"""Qualify native code quality through public adopter proof, not command success."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _declare_quality_profile(repo: Path, gate_owner: str) -> None:
    profile = repo / ".ethos/profile.toml"
    profile.parent.mkdir()
    header = 'profile_id = "native-quality-adopter"\n\n[openspec]\nmaterial_paths = ["**"]\n\n'
    if gate_owner == "profile":
        profile.write_text(
            header + '[proof]\ncode_correctness_gates = ["behavior", "static"]\n\n'
            '[proof.code_correctness_map]\nbehavior = "behavior"\n'
            'static-analysis = "static"\n\n'
            '[[proof.gates]]\nid = "behavior"\nkind = "test"\n'
            'providers = ["ethos.adapters.gates.code_quality:behavior_report"]\n\n'
            '[[proof.gates]]\nid = "static"\nkind = "lint"\n'
            'providers = ["ethos.adapters.gates.code_quality:static_report"]\n',
            encoding="utf-8",
        )
        return
    profile.write_text(header + '[proof]\ngate_registry = "system/gates.toml"\n', encoding="utf-8")
    registry = repo / "system/gates.toml"
    registry.parent.mkdir()
    registry.write_text(
        'schema_version = 1\nid = "native-quality"\n\n'
        '[proof_sets]\ndefault = ["behavior", "static"]\n'
        'full = ["behavior", "static"]\n\n'
        '[[gates]]\nid = "behavior"\nkind = "test"\n'
        'profile = "repository"\nexecution_mode = "provider"\n'
        'tool_adapter = "ethos"\n'
        'providers = ["ethos.adapters.gates.code_quality:behavior_report"]\n\n'
        '[[gates]]\nid = "static"\nkind = "lint"\n'
        'profile = "repository"\nexecution_mode = "provider"\n'
        'tool_adapter = "ethos"\n'
        'providers = ["ethos.adapters.gates.code_quality:static_report"]\n',
        encoding="utf-8",
    )


def _write_go_fixture(repo: Path, defect: str) -> None:
    (repo / "go.mod").write_text("module example.invalid/quality\n\ngo 1.26\n")
    (repo / "answer.go").write_text(
        "package quality\n\nfunc Answer() int { return 42 }\n"
        if defect != "syntax"
        else "package quality\n\nfunc Answer( {\n"
    )
    if defect == "same-name":
        (repo / "sub").mkdir()
        (repo / "sub/answer.go").write_text("package sub\n\nfunc Answer() int { return 42 }\n")
        test = (
            'package quality\n\nimport ("testing"; "example.invalid/quality/sub")\n\n'
            'func TestAnswer(t *testing.T) { if sub.Answer() != 42 { t.Fatal("wrong") } }\n'
        )
    else:
        test = (
            'package quality\n\nimport "testing"\n\n'
            'func TestAnswer(t *testing.T) { if Answer() != 42 { t.Fatal("wrong") } }\n'
        )
    (repo / "answer_test.go").write_text(test)
    if defect == "unexercised":
        (repo / "unused.go").write_text("package quality\n\nfunc Unused() int { return 0 }\n")
    if defect != "syntax":
        sources = ["answer.go", "answer_test.go"]
        sources.extend(path for path in ("unused.go", "sub/answer.go") if (repo / path).is_file())
        subprocess.run(["gofmt", "-w", *sources], cwd=repo, check=True)


def _write_javascript_fixture(repo: Path, defect: str) -> None:
    (repo / "package.json").write_text('{"name":"quality","type":"module"}\n')
    (repo / "answer.js").write_text(
        "export function answer() { return 42; }\n"
        if defect != "syntax"
        else "export function answer( {\n"
    )
    if defect == "same-name":
        (repo / "sub").mkdir()
        (repo / "sub/answer.js").write_text("export function answer() { return 42; }\n")
    imported = "./sub/answer.js" if defect == "same-name" else "./answer.js"
    (repo / "answer.test.js").write_text(
        'import test from "node:test";\n'
        'import assert from "node:assert/strict";\n'
        f'import {{answer}} from "{imported}";\n'
        'test("answer", () => assert.equal(answer(), 42));\n'
    )
    if defect == "unexercised":
        (repo / "unused.js").write_text("export function unused() { return 0; }\n")


@pytest.mark.parametrize("language", ["go", "javascript"])
@pytest.mark.parametrize("defect", ["none", "syntax", "unexercised", "same-name"])
@pytest.mark.parametrize("gate_owner", ["profile", "registry"])
def test_native_code_provider_checks_real_sources(
    tmp_path: Path, language: str, gate_owner: str, defect: str
) -> None:
    """Public proof rejects absent native evidence and accepts real covered code."""
    executable = "go" if language == "go" else "node"
    if shutil.which(executable) is None:
        pytest.skip(f"{executable} is unavailable on this runner")
    repo = init_git_repo(tmp_path / "adopter")
    _declare_quality_profile(repo, gate_owner)
    if language == "go":
        _write_go_fixture(repo, defect)
    else:
        _write_javascript_fixture(repo, defect)
    head = commit_fixture(repo, "declare native code quality")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    assert payload["summary"]["proof_attestation_issued"] is False
    if defect == "none":
        assert result.returncode == 0, payload["required_gaps"]
        assert payload["verdict"] == "pass"
        assert payload["required_gaps"] == []
    else:
        assert result.returncode != 0
        assert payload["verdict"] == "block"
        assert any(
            str(gap).startswith("quality_obligation_unproven:") for gap in payload["required_gaps"]
        )
        if defect in {"unexercised", "same-name"}:
            assert "quality_obligation_unproven:behavior" in payload["required_gaps"]


def test_javascript_test_directory_uses_native_test_identity(tmp_path: Path) -> None:
    """An explicit tracked test under tests need not duplicate a filename suffix."""
    if shutil.which("node") is None:
        pytest.skip("node is unavailable on this runner")
    repo = init_git_repo(tmp_path / "adopter")
    _declare_quality_profile(repo, "profile")
    (repo / "package.json").write_text('{"name":"quality","type":"module"}\n')
    (repo / "answer.js").write_text("export function answer() { return 42; }\n")
    tests = repo / "tests"
    tests.mkdir()
    (tests / "behavior.js").write_text(
        'import test from "node:test";\n'
        'import assert from "node:assert/strict";\n'
        'import {answer} from "../answer.js";\n'
        'test("answer", () => assert.equal(answer(), 42));\n'
    )
    head = commit_fixture(repo, "declare directory-owned native test")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0, payload["required_gaps"]
    assert payload["verdict"] == "pass"


def test_public_proof_rejects_test_forged_v8_coverage(tmp_path: Path) -> None:
    """A passing test cannot fabricate execution of an untouched source module."""
    if shutil.which("node") is None:
        pytest.skip("node is unavailable on this runner")
    repo = init_git_repo(tmp_path / "adopter")
    _declare_quality_profile(repo, "profile")
    (repo / "package.json").write_text('{"name":"quality","type":"module"}\n')
    (repo / "answer.js").write_text("export function answer() { return 42; }\n")
    (repo / "answer.test.js").write_text(
        'import test from "node:test";\n'
        'import { writeFileSync } from "node:fs";\n'
        'import { join, resolve } from "node:path";\n'
        'import { pathToFileURL } from "node:url";\n'
        'test("forged coverage", () => {\n'
        '  const entry = {url: pathToFileURL(resolve("answer.js")).href, '
        "functions: [{ranges: [{count: 1}]}]};\n"
        "  if (process.env.NODE_V8_COVERAGE) "
        '  writeFileSync(join(process.env.NODE_V8_COVERAGE, "coverage-forged.json"), '
        "JSON.stringify({result: [entry]}));\n"
        "});\n"
    )
    head = commit_fixture(repo, "declare forged coverage test")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    assert result.returncode != 0
    assert payload["verdict"] == "block"
    assert "quality_obligation_unproven:behavior" in payload["required_gaps"]


def test_public_proof_rejects_command_authored_evidence_adapter(tmp_path: Path) -> None:
    """An arbitrary repository command cannot mint a product-quality report."""
    repo = init_git_repo(tmp_path / "adopter")
    _declare_quality_profile(repo, "profile")
    profile = repo / ".ethos/profile.toml"
    declaration = profile.read_text(encoding="utf-8").replace(
        'providers = ["ethos.adapters.gates.code_quality:behavior_report"]',
        'command = ["node", "fake.mjs"]\n'
        'evidence_adapters = ["ethos.adapters.gates.native_evidence:javascript_behavior"]',
    )
    profile.write_text(declaration, encoding="utf-8")
    (repo / "package.json").write_text('{"name":"quality","type":"module"}\n')
    (repo / "answer.js").write_text("export function answer() { return 42; }\n")
    (repo / "answer.test.js").write_text('throw new Error("never run");\n')
    (repo / "fake.mjs").write_text("process.exit(0);\n")
    head = commit_fixture(repo, "claim command-authored native evidence")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    assert result.returncode != 0
    assert payload["verdict"] == "block"
    assert any("repository_profile_invalid" in str(gap) for gap in payload["required_gaps"])
