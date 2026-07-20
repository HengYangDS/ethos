"""Coverage-closure edge tests for the repository cluster."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import ethos.repository.audit as repository_audit
import ethos.repository.design.integrity as design_integrity
import ethos.repository.policy.coupling.registry as coupling_registry
import ethos.repository.policy.rules.evaluation as rule_evaluation
import ethos.repository.policy.rules.exceptions as rule_exceptions
import ethos.repository.registry.docs.commands as docs_commands
import ethos.repository.registry.docs.links as docs_links
from ethos.repository.evidence.parity.validation import command_matches_identity
from ethos.repository.evidence.parity.validation import semantic_tree_digest
from ethos.repository.evidence.parity.validation import validate_parity_evidence
from ethos.repository.openspec.metadata import is_relative_to
from ethos.repository.openspec.metadata import read_openspec_metadata
from ethos.repository.policy import schema as policy_schema
from tests.unit.product.parity.snapshots import complete_parity_evidence

if TYPE_CHECKING:
    import pytest


def test_repository_core_edges(tmp_path: Path) -> None:
    metadata = tmp_path / ".openspec.yaml"
    metadata.write_text("# comment\n\n   \nschema: spec-driven\n  # comment\nstatus: active\n", encoding="utf-8")  # fmt: skip
    assert read_openspec_metadata(metadata) == {"schema": "spec-driven", "status": "active"}
    assert semantic_tree_digest(tmp_path, head="", relevant_paths=("a.py",)) == ""
    evidence = complete_parity_evidence("generic")
    evidence["verified_capabilities"] = None
    gaps = validate_parity_evidence(evidence, "generic")
    assert ("parity_evidence_invalid:generic:verified_capabilities" in gaps, "parity_evidence_invalid:generic:unknown_capability" in gaps, "parity_evidence_invalid:generic:capability_basis" in gaps) == (True, False, False)  # fmt: skip
    assert command_matches_identity("ethos parity shadow --adopter generic --execute --json", adopter="generic", target=None) is False  # fmt: skip
    evidence = complete_parity_evidence("generic")
    freshness = evidence["freshness"]
    assert isinstance(freshness, dict)
    del freshness["product_head"]
    assert "parity_evidence_invalid:generic:product_head" in validate_parity_evidence(evidence, "generic")  # fmt: skip


def test_repository_schema_and_policy_edges(  # noqa: PLR0915, RUF100 - related repository edge matrix
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(policy_schema, "_schema_dir_has_contracts", lambda _path: False)
    product_dir = policy_schema._product_schema_dir  # noqa: SLF001, RUF100 - fallback edge
    assert product_dir() == Path.cwd() / "system/schemas/kernel"
    kernel = tmp_path / "system/schemas/kernel"
    kernel.mkdir(parents=True)
    (kernel / "broken.schema.json").write_text("{", encoding="utf-8")
    monkeypatch.setattr(policy_schema, "_effective_schema_dir", lambda _root: kernel)
    monkeypatch.setattr(policy_schema, "_instance_validation_report", lambda _root, **_kwargs: {})
    report = policy_schema.schema_validation_report(tmp_path)
    assert (report["ok"], report["schemas"]["broken.schema.json"]["ok"], "error" in report["schemas"]["broken.schema.json"]) == (False, False, True)  # fmt: skip
    assert any(gap.startswith("broken.schema.json:") for gap in report["required_gaps"])
    monkeypatch.undo()
    skills = tmp_path / ".agents/skills"
    (skills / "demo").mkdir(parents=True)
    (skills / "activation.toml").write_text("", encoding="utf-8")
    (skills / "demo/package.toml").write_text("[bad\n", encoding="utf-8")
    live = policy_schema._live_skill_contract_instances(tmp_path)  # noqa: SLF001, RUF100 - malformed manifest edge  # fmt: skip
    manifests = live["live-skill-package-manifests"]
    assert manifests["ok"] is False
    assert any(gap.startswith(".agents/skills/demo/package.toml:") for gap in manifests["required_gaps"])  # fmt: skip
    hooks = tmp_path / ".githooks"
    hooks.mkdir()
    (hooks / "pre-commit").touch()
    monkeypatch.setattr(repository_audit.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout=""))  # fmt: skip
    armed = repository_audit._write_admission_armed_gaps(tmp_path)  # noqa: SLF001, RUF100 - unwired hook edges  # fmt: skip
    assert set(armed) == {"write_admission_not_armed:pre-push_script_missing", "write_admission_not_armed:reference-transaction_script_missing", "write_admission_not_armed:core.hooksPath"}  # fmt: skip
    plain = tmp_path / "plain.md"
    plain.write_text("plain", encoding="utf-8")
    assert [design_integrity.front_matter_ok(path) for path in (tmp_path / "missing", plain)] == [False, False]  # fmt: skip
    assert is_relative_to(tmp_path, tmp_path / "other") is False
    bundle = policy_schema._bundle_node  # noqa: SLF001, RUF100 - recursive ref edge
    assert bundle({"$ref": "x.schema.json"}, root=tmp_path, seen=frozenset({"x.schema.json"})) == {"$ref": "x.schema.json"}  # fmt: skip
    capability = tmp_path / "openspec/specs/x/capability.toml"
    capability.parent.mkdir(parents=True)
    capability.write_text("[", encoding="utf-8")
    profiles = policy_schema._capability_profiles_report  # noqa: SLF001, RUF100 - malformed profile edge  # fmt: skip
    assert profiles(tmp_path, mode="product")["ok"] is False
    declaration = SimpleNamespace(layers=("known",), ui_projection_fields=(), bindings=())
    bindings = [{}, {"id": "x", "layer": "known"}, {"id": "x", "layer": "unknown"}]
    assert coupling_registry.binding_registry_gaps(bindings, declaration) == ["binding_registry_missing_id", "binding_registry_duplicate:x", "binding_registry_unknown_layer:x:unknown"]  # fmt: skip
    assert [rule_evaluation.scope_matches_path(scope, "x") for scope in ("repository", "path:")] == [True, False]  # fmt: skip
    exceptions = tmp_path / "rules/ethos/policy-exceptions.toml"
    exceptions.parent.mkdir(parents=True)
    exceptions.write_text("[", encoding="utf-8")
    assert rule_exceptions.policy_exceptions_report(tmp_path)["ok"] is False
    exceptions.write_text("exception = {}\n", encoding="utf-8")
    monkeypatch.setattr(rule_exceptions, "compile_rules", lambda _root: {"rules": []})
    assert rule_exceptions.policy_exceptions_report(tmp_path)["exceptions"] == []
    assert (docs_commands.tokens("'unterminated"), docs_commands.ethos_command_key("ethos")) == (["'unterminated"], "ethos")  # fmt: skip
    doc = tmp_path / "doc.md"
    doc.write_text("[self](#a)\nplain\n# A\n", encoding="utf-8")
    monkeypatch.setattr(docs_links, "markdown_paths", lambda _root: [doc])
    assert docs_links.link_integrity_report(tmp_path)["ok"] is True
