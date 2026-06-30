from __future__ import annotations

import json
from pathlib import Path

from ethos_kernel.action_graph import ActionGraph, ActionNode
from ethos_kernel.models import Change, Commitment, Evidence, Evolution, Subject
from ethos_kernel.result import EthosResult


def test_kernel_entities_project_to_chain() -> None:
    subject = Subject(
        id="repo:ethos",
        kind="repository",
        name="ETHOS",
        owner="ethos-maintainers",
    )
    commitment = Commitment(
        id="commitment:command-plane",
        subject_id=subject.id,
        kind="policy",
        statement="The public command plane is ethos.",
    )
    change = Change(
        id="change:bootstrap",
        subject_ids=(subject.id,),
        commitment_ids=(commitment.id,),
        transition="bootstrap product repository",
        inscriptions=("docs/concepts/kernel-model.md",),
    )
    evidence = Evidence(
        id="evidence:bootstrap",
        change_id=change.id,
        kind="test",
        refs=("tests/unit/test_kernel_contracts.py",),
        head="abc123",
    )
    evolution = Evolution(
        id="evolution:self",
        subject_id=subject.id,
        hypothesis="ETHOS can govern its own command plane.",
        state="hypothesis",
    )

    assert subject.chain_term == "subject"
    assert commitment.chain_term == "commitment"
    assert change.chain_term == "change"
    assert evidence.chain_term == "evidence"
    assert evolution.chain_term == "evolution"
    assert change.inscriptions == ("docs/concepts/kernel-model.md",)


def test_action_graph_is_deterministic_and_digest_bound() -> None:
    first = ActionNode(
        id="prove",
        kind="proof",
        command=("ethos", "prove", "--json"),
        inputs=("pyproject.toml", "packages/ethos/src/ethos/cli.py"),
        outputs=("docs/evidence/proof.json",),
        policy="required",
        tool="ethos",
        tool_version="0.1.0",
    )
    second = ActionNode(
        id="status",
        kind="inspection",
        command=("ethos", "status", "--json"),
        inputs=("packages/ethos/src/ethos/cli.py", "pyproject.toml"),
        outputs=(),
        policy="required",
        tool="ethos",
        tool_version="0.1.0",
    )

    graph = ActionGraph(nodes=(first, second))
    serialized = graph.to_dict()

    assert [node["id"] for node in serialized["nodes"]] == ["prove", "status"]
    assert graph.digest() == ActionGraph(nodes=(second, first)).digest()
    assert first.cache_key() != second.cache_key()


def test_result_contract_has_stable_top_level_fields() -> None:
    result = EthosResult(
        command="status",
        ok=True,
        state="ready",
        summary={"branch": "dev"},
        next_actions=("ethos plan --changed",),
    )

    payload = result.to_dict()

    assert tuple(payload) == (
        "schema_version",
        "command",
        "ok",
        "state",
        "summary",
        "diagnostics",
        "required_gaps",
        "next_actions",
        "data",
    )
    json.dumps(payload)


def test_json_schemas_are_declared_for_kernel_protocols() -> None:
    schema_dir = Path("schemas/ethos")
    expected = {
        "result.schema.json",
        "claim.schema.json",
        "commit-policy.schema.json",
        "subject.schema.json",
        "commitment.schema.json",
        "change.schema.json",
        "action.schema.json",
        "evidence.schema.json",
        "proof-run.schema.json",
        "evidence-set.schema.json",
        "provenance.schema.json",
        "chronicle.schema.json",
        "evolution.schema.json",
        "docs-registry.schema.json",
        "evolution-ledger.schema.json",
        "gate.schema.json",
        "assistant-projection.schema.json",
        "mutation-decision.schema.json",
        "workspace-status.schema.json",
    }

    assert expected <= {path.name for path in schema_dir.glob("*.schema.json")}


def test_json_schemas_are_valid_json_documents() -> None:
    for path in Path("schemas/ethos").glob("*.schema.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert payload["title"].startswith("ETHOS")
