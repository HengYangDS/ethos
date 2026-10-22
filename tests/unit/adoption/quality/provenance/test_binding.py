"""Bind native artifact materials and the actual product helper to gate identity."""

from __future__ import annotations

import hashlib
import json
import tomllib
from typing import TYPE_CHECKING

import pytest
import tomli_w

from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.contracts.gates import Gate
from ethos.repository.policy.gates import bind_gate_source_digests
from ethos.repository.profile import ProofPolicy
from ethos.repository.profile import SourceContract
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo
from tests.support.proof import declare_quality_profile

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("kind", ["generated", "upstream"])
def test_gate_identity_binds_complete_native_artifact_materials(tmp_path: Path, kind: str) -> None:
    """Old-tree binding is stable; every consumed producer or archive input changes identity."""
    repo = init_git_repo(tmp_path / "adopter")
    declare_quality_profile(repo)
    (repo / "authored.py").write_text("VALUE = 42\n")
    artifact = "snapshot.txt"
    (repo / artifact).write_text("original\n")
    if kind == "generated":
        declaration = ".config/checks/ci-projection/policy.toml"
        owner = repo / declaration
        owner.parent.mkdir(parents=True)
        (repo / "input.txt").write_text("original\n")
        owner.write_text(
            tomli_w.dumps(
                {
                    "schema": "ethos-ci-template-consistency-v1",
                    "projection": [{"template": "input.txt", "projection": artifact}],
                }
            )
        )
        reference, member, consumed = declaration, artifact, "input.txt"
    else:
        (repo / "upstream.tgz").write_bytes(b"locked original archive")
        (repo / "package-lock.json").write_text(
            json.dumps(
                {
                    "lockfileVersion": 3,
                    "packages": {
                        "node_modules/example": {
                            "resolved": "file:upstream.tgz",
                            "integrity": "sha512-native",
                        }
                    },
                }
            )
        )
        reference = "package-lock.json#packages/node_modules/example"
        member, consumed = "package/source.txt", "upstream.tgz"
    profile = repo / ".ethos/profile.toml"
    payload = tomllib.loads(profile.read_text())
    payload["proof"]["code_correctness_gates"].append("integrity")
    payload["proof"]["gates"].append(
        {
            "id": "integrity",
            "kind": "integrity",
            "providers": ["ethos.adapters.gates.provenance.observation:integrity_report"],
            "trust_bearing": True,
        }
    )
    payload["proof"]["source_contracts"] = [
        {
            "kind": kind,
            "input_refs": [reference],
            "members": {artifact: [reference, member]},
            "integrity_gate": "integrity",
        }
    ]
    profile.write_text(tomli_w.dumps(payload))
    head = commit_fixture(repo, "declare exact source inputs")
    before = resolve_gate_policy(repo, tree_ref=head, full=True)
    sources = dict(dict(before.sources)["integrity"])
    assert artifact in sources
    assert consumed in sources
    assert reference.partition("#packages/")[0] in sources
    helper = "@ethos/adapters/gates/provenance/archive.mjs"
    assert helper in sources
    (repo / consumed).write_text("changed native input\n")
    assert resolve_gate_policy(repo, tree_ref=head, full=True).digest == before.digest
    changed_head = commit_fixture(repo, "change one native input")
    changed = resolve_gate_policy(repo, tree_ref=changed_head, full=True)
    assert changed.digest != before.digest
    (repo / consumed).unlink()
    missing_head = commit_fixture(repo, "remove native input")
    (repo / consumed).write_text("untracked replacement\n")
    missing = resolve_gate_policy(repo, tree_ref=missing_head, full=True)
    assert f"gate_policy_source_missing:integrity:{consumed}" in missing.gaps


def test_gate_identity_binds_native_helper_not_only_python_entry() -> None:
    """A helper change or absence is visible in the existing gate-source contract."""
    gate = Gate(
        id="integrity",
        kind="integrity",
        profile="repository",
        tool_adapter="ethos",
        providers=("ethos.adapters.gates.provenance.observation:integrity_report",),
    )
    entry = "@ethos/adapters/gates/provenance/observation.py"
    helper = "@ethos/adapters/gates/provenance/archive.mjs"
    material = {
        entry: b"native entry",
        helper: b"native archive observer",
        "@ethos/repository/policy/quality/sources.py": b"native source relationships",
        "@ethos/adapters/repo/content/observation.py": b"bounded no-follow reads",
    }
    sources, gaps = bind_gate_source_digests((gate,), material)
    assert gaps == ()
    assert dict(dict(sources)["integrity"])[helper] == hashlib.sha256(material[helper]).hexdigest()
    for dependency in (helper, "@ethos/adapters/repo/content/observation.py"):
        changed, _gaps = bind_gate_source_digests(
            (gate,), {**material, dependency: b"changed observer"}
        )
        assert changed != sources
        assert bind_gate_source_digests(
            (gate,), {path: raw for path, raw in material.items() if path != dependency}
        )[1] == (f"gate_policy_source_missing:integrity:{dependency}",)


def test_generated_source_binding_preserves_compiler_inputs_and_complete_outputs() -> None:
    """Native CUE group identity includes auxiliary inputs, supply, and every output."""
    declaration = ".config/checks/ci-projection/policy.toml"
    outputs = [".github/workflows/ci.yml", ".gitlab-ci.yml"]
    contract = SourceContract.model_validate(
        {
            "kind": "generated",
            "input_refs": [declaration],
            "members": {output: [declaration, output] for output in outputs},
            "integrity_gate": "integrity",
        }
    )
    gate = Gate(
        id="integrity",
        kind="integrity",
        profile="repository",
        tool_adapter="ethos",
        providers=("ethos.adapters.gates.provenance.observation:integrity_report",),
    )
    dependencies = ["ci.cue", "inputs.json", ".config/mise/config.toml", ".config/mise/mise.lock"]
    product_helpers = (
        "@ethos/adapters/projections/compiler.py",
        "@ethos/adapters/projections/cue.py",
        "@ethos/adapters/toolchain/mise.py",
        "@ethos/adapters/repo/runtime/materialization/native_supply.py",
        "@ethos/repository/policy/projections.py",
        "@ethos/repository/release/resources.py",
    )
    material = {path: path.encode() for path in (*dependencies, *outputs, *product_helpers)}
    material.update(
        {
            "@ethos/adapters/gates/provenance/observation.py": b"native entry",
            "@ethos/adapters/gates/provenance/archive.mjs": b"native archive observer",
            "@ethos/repository/policy/quality/sources.py": b"native source relations",
            "@ethos/adapters/repo/content/observation.py": b"bounded no-follow reads",
            declaration: tomli_w.dumps(
                {
                    "schema": "ethos-ci-template-consistency-v1",
                    "compiler": {
                        "source": dependencies[0],
                        "inputs": {"policy": dependencies[1]},
                        "supply": {"config": dependencies[2], "lock": dependencies[3]},
                    },
                    "projection": [
                        {"kind": "cue", "provider": f"provider-{index}", "projection": output}
                        for index, output in enumerate(outputs)
                    ],
                }
            ).encode(),
        }
    )
    before, gaps = bind_gate_source_digests((gate,), material, source_contracts=(contract,))
    assert gaps == ()
    paths = dict(dict(before)["integrity"])
    assert {*dependencies, *outputs, *product_helpers, declaration} <= paths.keys()
    for path in (*dependencies, *outputs, *product_helpers):
        after, gaps = bind_gate_source_digests(
            (gate,), {**material, path: b"changed"}, source_contracts=(contract,)
        )
        assert gaps == ()
        assert before != after
    for path in product_helpers:
        _sources, gaps = bind_gate_source_digests(
            (gate,),
            {name: raw for name, raw in material.items() if name != path},
            source_contracts=(contract,),
        )
        assert gaps == (f"gate_policy_source_missing:integrity:{path}",)
    partial = SourceContract.model_validate(
        {
            "kind": "generated",
            "input_refs": [declaration],
            "members": {outputs[0]: [declaration, outputs[0]]},
            "integrity_gate": "integrity",
        }
    )
    _sources, gaps = bind_gate_source_digests((gate,), material, source_contracts=(partial,))
    assert any("source_producer_group_incomplete" in gap for gap in gaps)


@pytest.mark.parametrize(
    ("contract", "message"),
    [
        (
            {"input_refs": ["a.toml"], "members": {"out.js": ["b.toml", "out.js"]}},
            "use each distinct input reference",
        ),
        (
            {"input_refs": ["a//b.toml"], "members": {"out.js": ["a//b.toml", "out.js"]}},
            "exact repository path",
        ),
        (
            {"input_refs": ["a.toml#x"], "members": {"out.js": ["a.toml#x", "out.js"]}},
            "no supported native meaning",
        ),
        (
            {"input_refs": ["a.toml"], "members": {"out.js": ["a.toml", "other.js"]}},
            "exact native identity",
        ),
    ],
)
def test_source_contract_preserves_exact_native_relations(contract: dict, message: str) -> None:
    """A generated obligation binds each exact input once to its exact output member."""
    with pytest.raises(ValueError, match=message):
        SourceContract.model_validate(
            {"kind": "generated", "integrity_gate": "integrity", **contract}
        )


@pytest.mark.parametrize(
    ("policy", "message"),
    [
        (
            {
                "source_contracts": [
                    {
                        "kind": "generated",
                        "input_refs": [reference],
                        "members": {"out.js": [reference, "out.js"]},
                        "integrity_gate": "integrity",
                    }
                    for reference in ("a.toml", "b.toml")
                ]
            },
            "source artifact has parallel owners",
        ),
        (
            {"gate_registry": "system/gates.toml", "code_correctness_gates": ["tests"]},
            "proof policy has parallel gate owners",
        ),
    ],
)
def test_proof_policy_keeps_one_owner_per_artifact_and_gate(policy: dict, message: str) -> None:
    """Artifacts and the proof floor each keep exactly one declared owner."""
    with pytest.raises(ValueError, match=message):
        ProofPolicy.model_validate(policy)
