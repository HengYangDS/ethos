# ruff: noqa: ARG005, TC003, PLW0108, T201, PT018
# Monkeypatch-heavy coverage edge tests intentionally preserve callable signatures
# matching patched runtime functions; unused parameters document those contracts.

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import ethos.adapters.openspec.archive.core as archive_mod
import ethos.adapters.openspec.cli as openspec_cli
import ethos.adapters.openspec.core as openspec_core
import ethos.adapters.openspec.lifecycle.core as openspec_lifecycle
import ethos.adapters.openspec.metadata.core as openspec_metadata_adapter
import ethos.adapters.openspec.protocol.core as proposal_mod
from ethos.repository import openspec_metadata
from ethos.repository.policy import schema as policy_schema
from ethos.repository.registry.docs.commands import best_ethos_command_key
from ethos.repository.registry.docs.commands import command_examples_report
from ethos.repository.registry.docs.commands import command_root
from ethos.repository.registry.docs.commands import ethos_command_key
from ethos.repository.registry.docs.commands import ethos_invocation_tokens
from ethos.repository.registry.docs.commands import has_command_example
from ethos.repository.registry.docs.commands import known_ethos_command
from ethos.repository.registry.docs.commands import requires_product_examples
from ethos.repository.registry.docs.commands import tokens
from ethos.repository.registry.docs.health import docs_health_report
from ethos.repository.registry.docs.links import glossary_report
from ethos.repository.registry.docs.links import link_integrity_report
from ethos.repository.registry.docs.links import markdown_anchors
from ethos.repository.registry.docs.links import slugify_heading
from ethos.repository.registry.docs.links import stable_paths_report
from ethos.surface.cli import _base
from ethos.surface.cli import _gate_runner
from ethos.surface.cli import hook as hook_cli
from ethos_core.action_graph import ActionNode
from ethos_core.result import EthosResult


def cp(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["cmd"], returncode, stdout, stderr)


def test_openspec_base_json_selection_and_governance_edges(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ETHOS_OPENSPEC_BIN", "/opt/openspec")
    assert openspec_cli.openspec_base_command() == ("/opt/openspec",)
    monkeypatch.delenv("ETHOS_OPENSPEC_BIN")
    monkeypatch.setenv("ETHOS_NPX_CACHE_DIR", (tmp_path / "empty-npx-cache").as_posix())
    monkeypatch.setattr(
        openspec_cli.shutil, "which", lambda name: "/bin/openspec" if name == "openspec" else None
    )
    assert openspec_cli.openspec_base_command() == ("openspec",)
    monkeypatch.setattr(
        openspec_cli.shutil, "which", lambda name: "/bin/npx" if name == "npx" else None
    )
    assert openspec_cli.openspec_base_command() == (
        "npx",
        "--yes",
        openspec_cli.OFFICIAL_NPX_PACKAGE,
    )
    monkeypatch.setattr(openspec_cli.shutil, "which", lambda name: None)
    assert openspec_cli.openspec_base_command() is None

    assert openspec_lifecycle.selected_change({"changes": "bad"}, None) is None
    assert (
        openspec_lifecycle.selected_change(
            {"changes": [{"name": "a", "status": "in-progress"}]}, None
        )
        == "a"
    )
    assert (
        openspec_lifecycle.selected_change(
            {"changes": [{"name": "a", "lastModified": "1"}, {"name": "b", "lastModified": "2"}]},
            None,
        )
        == "b"
    )
    assert openspec_lifecycle.validation_failures({"items": "bad"}) == [
        "openspec_validation_unreadable"
    ]
    assert openspec_lifecycle.validation_failures(
        {"items": [{"valid": False, "type": "spec", "id": "x"}, "bad"]}
    ) == ["openspec_validation_failed:spec:x"]

    monkeypatch.setattr(
        openspec_cli.subprocess, "run", lambda *args, **kwargs: cp(stdout="[]", returncode=0)
    )
    result = openspec_cli.run_json(tmp_path, ("openspec",), ("list", "--json"))
    assert result["parse_error"] == "openspec_json_not_object"
    monkeypatch.setattr(
        openspec_cli.subprocess, "run", lambda *args, **kwargs: cp(stdout="{bad", returncode=0)
    )
    assert openspec_cli.run_json(tmp_path, ("openspec",), ("list", "--json"))["parse_error"]

    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: None)
    report = openspec_core.openspec_governance_report(tmp_path, change="c1", lifecycle=True)
    assert set(report["required_gaps"]) >= {
        "openspec_directory_missing",
        "openspec_official_cli_missing",
    }

    (tmp_path / "openspec" / "specs").mkdir(parents=True)
    (tmp_path / "openspec" / "config.yaml").write_text("spec-driven\n", encoding="utf-8")
    calls: list[tuple[str, ...]] = []

    def fake_run_json(
        root: Path, base: tuple[str, ...], args: tuple[str, ...]
    ) -> dict[str, object]:
        calls.append(args)
        if args[:1] == ("doctor",):
            return {
                "exit_code": 1,
                "json": {"root": {"healthy": False}},
                "parse_error": "",
                "stdout": "",
                "stderr": "",
                "command": [],
            }
        if args[:1] == ("list",):
            return {
                "exit_code": 1,
                "json": {"changes": [{"name": "c1", "status": "in-progress"}]},
                "parse_error": "bad-list",
                "stdout": "",
                "stderr": "",
                "command": [],
            }
        if args[:1] == ("status",):
            return {
                "exit_code": 1,
                "json": {"isComplete": False, "schemaName": "s"},
                "parse_error": "bad-status",
                "stdout": "",
                "stderr": "",
                "command": [],
            }
        return {
            "exit_code": 1,
            "json": {"items": [{"valid": False, "type": "cap", "id": "x"}]},
            "parse_error": "bad-validate",
            "stdout": "",
            "stderr": "",
            "command": [],
        }

    monkeypatch.setattr(openspec_cli, "run_json", fake_run_json)
    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: ("openspec",))
    governed = openspec_core.openspec_governance_report(tmp_path, lifecycle=True)
    assert "openspec_doctor_unhealthy" in governed["required_gaps"]
    assert "openspec_list_failed" in governed["required_gaps"]
    assert "openspec_status_incomplete:c1" in governed["required_gaps"]
    assert "openspec_validation_failed:cap:x" in governed["required_gaps"]
    assert "openspec_list_json_parse_failed" in governed["required_gaps"]
    assert "openspec_status_json_parse_failed" in governed["required_gaps"]
    assert "openspec_validate_json_parse_failed" in governed["required_gaps"]
    assert any(call[:1] == ("status",) for call in calls)


def test_openspec_cached_cli_entry_skips_invalid_cache_candidates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cache = tmp_path / "_npx"
    bad_json = cache / "bad-json" / "node_modules" / "@fission-ai" / "openspec"
    missing_bin = cache / "missing-bin" / "node_modules" / "@fission-ai" / "openspec"
    string_bin = cache / "string-bin" / "node_modules" / "@fission-ai" / "openspec"
    no_entry = cache / "no-entry" / "node_modules" / "@fission-ai" / "openspec"
    numeric_bin = cache / "numeric-bin" / "node_modules" / "@fission-ai" / "openspec"
    for package_root in (bad_json, missing_bin, string_bin, no_entry, numeric_bin):
        package_root.mkdir(parents=True)
    (bad_json / "package.json").write_text("{bad", encoding="utf-8")
    (missing_bin / "package.json").write_text(
        '{"version":"1.0.0","bin":{"openspec":"missing.js"}}',
        encoding="utf-8",
    )
    (string_bin / "package.json").write_text(
        '{"version":"2.0.0","bin":"bin/openspec.js"}',
        encoding="utf-8",
    )
    (string_bin / "bin").mkdir()
    (string_bin / "bin" / "openspec.js").write_text("#!/usr/bin/env node\n", encoding="utf-8")
    (no_entry / "package.json").write_text(
        '{"version":"3.0.0","bin":{"other":"bin/other.js"}}',
        encoding="utf-8",
    )
    (numeric_bin / "package.json").write_text(
        '{"version":"4.0.0","bin":123}',
        encoding="utf-8",
    )

    monkeypatch.setenv("ETHOS_NPX_CACHE_DIR", cache.as_posix())
    monkeypatch.setattr(openspec_cli.shutil, "which", lambda name: "/usr/bin/node")

    assert openspec_cli.cached_official_cli_entry() == (
        "/usr/bin/node",
        (string_bin / "bin" / "openspec.js").resolve().as_posix(),
    )

    (string_bin / "bin" / "openspec.js").unlink()
    assert openspec_cli.cached_official_cli_entry() is None


def test_openspec_archive_and_lifecycle_protocol_edges(tmp_path: Path) -> None:
    assert openspec_metadata_adapter.completed_active_changes_report(tmp_path)["ok"] is True
    archive = tmp_path / "openspec" / "changes" / "archive" / "bad_name"
    (archive / "specs" / "cap").mkdir(parents=True)
    (archive / "proposal.md").write_text("proposal", encoding="utf-8")
    (archive / "design.md").write_text("", encoding="utf-8")
    (archive / "tasks.md").write_text("- [ ] todo\n", encoding="utf-8")
    (archive / ".openspec.yaml").write_text(
        "schema: other\ncreated: 9999-99-99\n", encoding="utf-8"
    )
    (archive / "specs" / "cap" / "spec.md").write_text("No delta\n", encoding="utf-8")
    report = archive_mod.openspec_archive_closeout_report(tmp_path)
    gaps = set(report["required_gaps"])
    assert "openspec_archive_name_invalid:bad_name" in gaps
    assert "openspec_archive_metadata_schema_invalid:bad_name" in gaps
    assert "openspec_archive_design_empty:bad_name" in gaps
    assert "openspec_archive_tasks_incomplete:bad_name" in gaps
    assert "openspec_archive_delta_header_missing:bad_name" in gaps
    assert "openspec_archive_delta_requirement_missing:bad_name" in gaps
    assert "openspec_archive_delta_scenario_missing:bad_name" in gaps
    assert (
        archive_mod.archive_delta_issues(
            tmp_path / "missing-specs", archive_name="a", root=tmp_path
        )[0]["gap"]
        == "openspec_archive_delta_specs_missing:a"
    )

    assert openspec_metadata_adapter.completed_active_change_names(
        {"changes": [{"name": "done", "status": "complete"}, {"id": "x", "state": "done"}, "bad"]}
    ) == ["done", "x"]
    assert openspec_metadata.read_openspec_metadata(archive / ".openspec.yaml")["schema"] == "other"
    assert openspec_metadata.is_relative_to(tmp_path / "x", tmp_path) is True
    assert openspec_metadata.is_relative_to(tmp_path.parent, tmp_path) is False

    change_root = tmp_path / "openspec" / "changes" / "c1"
    (change_root / "specs").mkdir(parents=True)
    (change_root / "proposal.md").write_text(
        "# Proposal\n\n- `cap`: reuse=wrong; change=sideways; subject=; facet:lifecycle=; facet:surface=; facet:authority=\n",
        encoding="utf-8",
    )
    lifecycle = openspec_lifecycle.lifecycle_report(
        tmp_path, selected="c1", list_payload={}, enabled=True
    )
    assert "openspec_design_missing:c1" in lifecycle["required_gaps"]
    assert "openspec_tasks_missing:c1" in lifecycle["required_gaps"]
    assert "openspec_delta_specs_missing:c1" in lifecycle["required_gaps"]
    assert "openspec_claim_binding_missing:c1" in lifecycle["required_gaps"]
    assert "openspec_proposal_out_of_scope_missing:c1" in lifecycle["required_gaps"]
    assert "openspec_proposal_capability_unknown:c1:cap" in lifecycle["required_gaps"]
    assert "openspec_capability_profile_missing:c1:cap" in lifecycle["required_gaps"]
    assert "openspec_proposal_reuse_invalid:c1:cap:wrong" in lifecycle["required_gaps"]
    assert "openspec_proposal_change_invalid:c1:cap:sideways" in lifecycle["required_gaps"]

    spec = tmp_path / "openspec" / "specs" / "cap"
    spec.mkdir(parents=True)
    (spec / "spec.md").write_text("spec", encoding="utf-8")
    (spec / "capability.toml").write_text("[bad\n", encoding="utf-8")
    assert proposal_mod.capability_profile_gaps(tmp_path, "c1", "cap") == [
        "openspec_capability_profile_invalid:c1:cap"
    ]


def test_docs_registry_links_commands_and_taxonomy_edges(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text(
        "---\nsubject: same\nrole: guide\nstate: active\nrelations: []\n---\n# A\n[missing](missing.md)\n[bad](#nope)\n```bash\nfoo bar\nethos unknown\n```\n",
        encoding="utf-8",
    )
    (docs / "b.md").write_text(
        "---\nsubject: same\nrole: guide\nstate: active\nrelations:\n  - x\n---\n# Known Anchor\nStatus: ok\nPurpose: ok\nSee also: ok\n",
        encoding="utf-8",
    )
    meta = docs / "_meta"
    meta.mkdir()
    (meta / "taxonomy.toml").write_text("[states]\nallowed=['active']\n", encoding="utf-8")
    health = docs_health_report(tmp_path)
    assert any(gap.startswith("duplicate_subject:same") for gap in health["required_gaps"])
    assert "missing_visible_section:docs/a.md:status" in health["required_gaps"]

    links = link_integrity_report(tmp_path)
    assert "broken_link:docs/a.md:8:missing.md" in links["required_gaps"]
    assert "broken_anchor:docs/a.md:9:#nope" in links["required_gaps"]
    assert markdown_anchors(docs / "b.md") == {"known-anchor"}
    assert slugify_heading("`Hello_World`!") == "hello-world"

    assert tokens("unterminated 'quote") == ["unterminated", "'quote"]
    assert command_root("env FOO=1 uv run --package ethos ethos prove --json") == "ethos"
    assert ethos_invocation_tokens(["python", "-m", "ethos.cli", "status"]) == [
        "ethos",
        "status",
    ]
    assert ethos_command_key("ethos") == "ethos"
    assert best_ethos_command_key("ethos playbooks missing") == "ethos playbooks missing"
    assert known_ethos_command("ethos playbooks route --changed") is True
    assert known_ethos_command("ethos playbooks missing") is False

    examples = command_examples_report(tmp_path)
    assert any(
        gap.startswith("unknown_command_example:docs/a.md") for gap in examples["required_gaps"]
    )
    assert any(
        gap.startswith("unknown_ethos_command_example:docs/a.md")
        for gap in examples["required_gaps"]
    )
    assert (
        has_command_example([{"scope": "archive", "command": "ethos prove"}], "ethos prove")
        is False
    )
    assert (
        requires_product_examples([{"scope": "current", "command": "ethos prove --json"}]) is True
    )

    glossary = docs / "reference"
    glossary.mkdir()
    (glossary / "glossary.md").write_text("## Command Plane\n", encoding="utf-8")
    assert any(
        gap.startswith("glossary_term_missing:")
        for gap in glossary_report(tmp_path)["required_gaps"]
    )
    (meta / "stable_paths.toml").write_text(
        "[[stable_path]]\npath='docs/missing.md'\n", encoding="utf-8"
    )
    assert (
        "stable_path_target_missing:docs/missing.md"
        in stable_paths_report(tmp_path)["required_gaps"]
    )
    (meta / "stable_paths.toml").write_text("[[stable_path]\n", encoding="utf-8")
    assert stable_paths_report(tmp_path)["required_gaps"] == ["stable_paths_invalid_toml"]


def test_schema_live_skill_invalid_and_adopter_profile_edges(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".agents" / "skills").mkdir(parents=True)
    (tmp_path / ".agents" / "skills" / "activation.toml").write_text("[bad\n", encoding="utf-8")
    live = policy_schema._live_skill_contract_instances(tmp_path)
    assert set(live) == {
        "live-skill-activation-contract",
        "live-skill-registry-contract",
        "live-skill-package-manifests",
    }
    assert all(item["ok"] is False for item in live.values())

    specs = tmp_path / "openspec" / "specs" / "cap"
    specs.mkdir(parents=True)
    (specs / "capability.toml").write_text("[bad\n", encoding="utf-8")
    product = policy_schema._capability_profiles_report(tmp_path, mode="product")
    adopter = policy_schema._capability_profiles_report(tmp_path, mode="adopter")
    assert product["required_gaps"]
    assert adopter["required_gaps"] == []
    assert adopter["advisory_gaps"]

    monkeypatch.setattr(
        policy_schema,
        "load_schema",
        lambda name, root=None: (
            {"$ref": "self.schema.json"}
            if name == "self.schema.json"
            else {"items": [{"$ref": "self.schema.json"}]}
        ),
    )
    bundled = policy_schema._bundle_local_refs({"$ref": "other.schema.json"}, root=tmp_path)
    assert bundled == {"items": [{"$ref": "self.schema.json"}]}


def test_cli_emit_load_gate_and_hook_install_edges(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    digest_file = tmp_path / "digest.txt"
    digest_file.write_text("ethos\n", encoding="utf-8")
    assert _base.sha256_file(digest_file).startswith("sha256:")

    ok_result = EthosResult(command="demo", ok=True, state="ready", next_actions=("next action",))
    _base.emit(ok_result, json_output=False)
    captured = capsys.readouterr().out
    assert "demo: ready" in captured
    assert "next: next action" in captured
    with pytest.raises(SystemExit):
        _base.emit(EthosResult(command="demo", ok=False, state="blocked"), json_output=True)
    assert '"ok": false' in capsys.readouterr().out

    imported: list[str] = []
    monkeypatch.setattr("importlib.import_module", lambda name: imported.append(name))
    _base.load_command_groups(["quality", "docs"])
    assert imported == ["ethos.surface.cli.quality"]
    imported.clear()
    _base.load_command_groups([])
    assert "ethos.surface.cli.hook" in imported
    imported.clear()
    _base.load_command_groups(["status"])
    assert imported == []

    node = ActionNode(
        id="a", kind="command", command=("python", "-m", "ethos.cli", "status", "--json")
    )
    monkeypatch.setattr(_gate_runner, "_load_command_groups", lambda argv: None)
    monkeypatch.setattr(
        _gate_runner,
        "app",
        lambda argv, exit_on_error=False: print(
            '{"ok": true, "command": "status", "required_gaps": []}'
        ),
    )
    gate = _gate_runner.run_inprocess_cli_gate(node, tmp_path)
    assert gate is not None and gate.exit_code == 0
    assert (
        _gate_runner.run_inprocess_cli_gate(
            ActionNode(id="b", kind="command", command=("ethos", "status")), tmp_path
        )
        is None
    )
    monkeypatch.setattr(
        _gate_runner, "app", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    failed = _gate_runner.run_inprocess_cli_gate(
        ActionNode(id="c", kind="command", command=("ethos", "status", "--json")), tmp_path
    )
    assert failed is not None and failed.exit_code == 1 and "RuntimeError" in failed.stderr

    monkeypatch.setattr(hook_cli, "resolve_root", lambda root: tmp_path)
    emitted: list[EthosResult] = []
    monkeypatch.setattr(
        hook_cli, "emit", lambda result, json_output, enforce=True: emitted.append(result)
    )
    hook_cli.install(json_output=True)
    assert emitted[-1].required_gaps == (
        "hook_script_missing:.githooks/pre-commit",
        "hook_script_missing:.githooks/pre-push",
        "hook_script_missing:.githooks/reference-transaction",
    )
    hooks = tmp_path / ".githooks"
    hooks.mkdir()
    for name in ("pre-commit", "pre-push", "reference-transaction"):
        (hooks / name).write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(hook_cli._gitio, "set_hooks_path", lambda repo, value: False)
    hook_cli.install(json_output=True)
    assert emitted[-1].required_gaps == ("hooks_path_wire_failed",)
    monkeypatch.setattr(hook_cli._gitio, "set_hooks_path", lambda repo, value: True)
    hook_cli.install(json_output=True)
    assert emitted[-1].ok is True

    monkeypatch.setattr(
        hook_cli,
        "push_admission_report",
        lambda **kwargs: {
            "ok": False,
            "state": "blocked",
            "target_branch": "dev",
            "role": "accepted_root",
            "decision": {},
            "required_gaps": ["gap"],
        },
    )
    hook_cli.pre_push("refs/heads/dev", "h1", json_output=True)
    assert emitted[-1].command == "hook pre-push"
    monkeypatch.setattr(
        hook_cli,
        "ref_move_admission_report",
        lambda **kwargs: {
            "ok": False,
            "state": "blocked",
            "branch": "dev",
            "decision": {},
            "required_gaps": ["gap"],
        },
    )
    hook_cli.ref_transaction("refs/heads/dev", "a", "b", json_output=True)
    assert emitted[-1].command == "hook ref-transaction"
