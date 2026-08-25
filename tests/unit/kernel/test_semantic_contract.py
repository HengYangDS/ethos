from __future__ import annotations

import json
import os
import subprocess
import tarfile
import tomllib
import zipfile
from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest
import tomli_w
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st
from pydantic import ValidationError

from ethos.adapters.repo.runtime.authority import runtime_build_identity
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import load_commitment_file
from ethos.repository.release.identity import wheel_build_identity
from tests.support.semantic import commitment_fixture
from tools.ci.delivery.pipeline import DeliveryPipeline
from tools.ci.toolchain.environment import ProjectRuntime

_JSON_SCALAR = (
    st.none()
    | st.booleans()
    | st.integers(min_value=-9_007_199_254_740_991, max_value=9_007_199_254_740_991)
    | st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=24)
)
_JSON_OBJECT = st.recursive(
    _JSON_SCALAR,
    lambda children: (
        st.lists(children, max_size=4)
        | st.dictionaries(
            st.text(alphabet=st.characters(blacklist_categories=("Cs",)), min_size=1, max_size=12),
            children,
            max_size=4,
        )
    ),
    max_leaves=12,
).map(lambda value: value if isinstance(value, dict) else {"value": value})


def _attestation_payload() -> dict[str, object]:
    return {
        "schema_version": 2,
        "predicate": "observation:repository",
        "verifier": "agent:codex:task:model-promotion",
        "subject": "change:model-promotion-successor",
        "issued_at": datetime(2026, 8, 14, 12, 34, 56, 123400, tzinfo=UTC),
        "valid_from": None,
        "valid_until": None,
        "verdict": "pass",
        "payload": {
            "kind": "input:feedback",
            "body": {
                "occurrence": {"ordinal": 1, "source": "conversation:task"},
                "text": "Preserve this occurrence.",
            },
        },
        "relations": [
            {
                "kind": "relation:selected-for",
                "target_kind": "semantic:commitment",
                "target_id": "change:model-promotion-successor",
                "attributes": {},
            }
        ],
        "advisories": [],
        "evidence_refs": ["evidence:conversation:one"],
        "commitment_digest": "1" * 64,
        "facts_digest": None,
        "plan_digest": None,
        "policy_digest": None,
        "effect_digest": None,
        "mints_authority": False,
    }


def _commitment_payload() -> dict[str, object]:
    return commitment_fixture(
        id="change:model-promotion-successor",
        intent="Adopt one selected input.",
        subjects=("repository:ethos",),
        scope=("src/ethos/contracts/semantic.py",),
        hypotheses=(
            {
                "id": "hypothesis:bounded-input",
                "kind": "hypothesis:causal",
                "body": {"proposition": "bounded"},
            },
        ),
        falsifiers=(
            {
                "id": "falsifier:expanded",
                "hypothesis_id": "hypothesis:bounded-input",
                "kind": "observation:repository",
                "body": {},
            },
        ),
        experiment_protocols=(
            {
                "id": "protocol:selection",
                "hypothesis_ids": ("hypothesis:bounded-input",),
                "kind": "experiment:repository",
                "body": {},
            },
        ),
    ).model_dump(mode="python")


def test_commitment_fixture_runtime_validation_matrix(tmp_path: Path) -> None:
    payload = _commitment_payload()
    repository_id = "repository:2454ddfb-3395-497b-b07c-416ac2e3a0ad"
    assert (
        Commitment.model_validate(payload | {"id": repository_id, "subjects": [repository_id]}).id
        == repository_id
    )
    for field in payload:
        with pytest.raises(ValidationError):
            Commitment.model_validate(
                {key: value for key, value in payload.items() if key != field}
            )

    carrier = tmp_path / "commitment.toml"
    carrier.write_text(tomli_w.dumps(payload | {"subjects": ["repository:self"]}), encoding="utf-8")
    with pytest.raises(ValidationError, match="commitment_string_value_invalid"):
        load_commitment_file(carrier)

    invalid = (
        ({"intent": " "}, "commitment_string_value_invalid"),
        ({"scope": [" "]}, "change_scope_invalid"),
        (
            {
                "dependencies": [
                    {"kind": "dependency:requires", "target": "value", "attributes": {1: "x"}}
                ]
            },
            "object_key_invalid",
        ),
        (
            {"hypotheses": [*payload["hypotheses"], payload["hypotheses"][0]]},
            "commitment_hypothesis_id_duplicate",
        ),
        (
            {"falsifiers": [dict(payload["falsifiers"][0], hypothesis_id="hypothesis:missing")]},
            "commitment_hypothesis_reference_missing",
        ),
        (
            {
                "experiment_protocols": [
                    dict(payload["experiment_protocols"][0], hypothesis_ids=["hypothesis:missing"])
                ]
            },
            "commitment_hypothesis_reference_missing",
        ),
    )
    for update, error in invalid:
        with pytest.raises((TypeError, ValidationError), match=error):
            Commitment.model_validate(payload | update)

    subjects = ["repository:\ue000", "repository:\U00010000"]
    ordered = Commitment.model_validate(payload | {"subjects": subjects})
    assert ordered.subjects == tuple(subjects)
    with pytest.raises(ValidationError, match="semantic_collection_order_invalid"):
        Commitment.model_validate(payload | {"subjects": list(reversed(subjects))})


def test_attestation_invalid_field_and_relation_matrix() -> None:
    payload = _attestation_payload()
    missing = {key: value for key, value in payload.items() if key != "facts_digest"}
    duplicate = dict(payload["relations"][0], attributes={"different": True})
    invalid = (
        (missing, None),
        (payload | {"mints_authority": True}, None),
        (
            payload | {"relations": [*payload["relations"], duplicate]},
            "attestation_relation_identity_duplicate",
        ),
        (payload | {"verifier": " "}, "commitment_string_value_invalid"),
        (payload | {"evidence_refs": [" "]}, "commitment_string_value_invalid"),
    )
    for candidate, error in invalid:
        with pytest.raises(ValidationError, match=error):
            Attestation.issue(candidate)


@pytest.mark.parametrize(
    ("raw", "strict", "error"),
    [
        (b'{"schema_version":2,"schema_version":2}', None, "semantic_object_key_duplicate"),
        (lambda value: b" " + value, None, "semantic_json_noncanonical"),
        (lambda value: value + b"\n", False, "semantic_json_noncanonical"),
        (
            lambda value: value.replace(b'"schema_version":2', b'"schema_version":2.5'),
            None,
            "semantic_json_value_invalid",
        ),
    ],
)
def test_semantic_json_reader_negative_matrix(raw, strict, error: str) -> None:
    canonical = Commitment.model_validate(_commitment_payload()).canonical_json().encode()
    candidate = raw(canonical) if callable(raw) else raw
    kwargs = {} if strict is None else {"strict": strict}
    with pytest.raises(ValueError, match=error):
        Commitment.model_validate_json(candidate, **kwargs)


@settings(max_examples=40, deadline=None)
@given(body=_JSON_OBJECT)
def test_attestation_unknown_payload_round_trips_without_authority(body: object) -> None:
    issued = Attestation.issue(
        _attestation_payload() | {"payload": {"kind": "input:future-feedback", "body": body}}
    )
    restored = Attestation.model_validate_json(issued.canonical_json())

    assert restored == issued
    assert restored.id == issued.id
    assert restored.payload.kind == "input:future-feedback"
    assert restored.relations[0].kind == "relation:selected-for"
    assert restored.mints_authority is False


def test_semantic_contract_golden_vectors_are_exact_in_source_wheel_and_sdist(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[3]
    vector_path = root / "tests/fixtures/semantic-contract/vectors.json"
    source_bytes = vector_path.read_bytes()
    vectors = json.loads(source_bytes)
    assert vectors["schema_version"] == 1
    commitment_vector, attestation_vector = vectors["commitment"], vectors["attestation"]
    commitment_path = tmp_path / "commitment.toml"
    commitment_path.write_text(commitment_vector["carrier_toml"], encoding="utf-8")
    commitment = load_commitment_file(commitment_path)
    attestation = Attestation.model_validate_json(attestation_vector["carrier_json"])

    assert (commitment.canonical_json(), commitment.digest()) == (
        commitment_vector["canonical_json"],
        commitment_vector["digest"],
    )
    assert (attestation.canonical_json(exclude_id=True), attestation.id) == (
        attestation_vector["canonical_json_without_id"],
        attestation_vector["id"],
    )
    build = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    force_include = build["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    assert force_include["tests/fixtures/semantic-contract/vectors.json"] == (
        "ethos/data/semantic-contract/vectors.json"
    )

    runtime = ProjectRuntime.discover(root)
    delivery = DeliveryPipeline.from_runtime(runtime)
    artifacts = tmp_path / "artifacts"
    subprocess.run(
        (
            runtime.script("uv"),
            "build",
            "--offline",
            "--out-dir",
            str(artifacts),
            "--clear",
            "--no-create-gitignore",
        ),
        cwd=root,
        env={
            **os.environ,
            "ETHOS_BUILD_NODE": str(delivery.node),
            "ETHOS_BUILD_NPM_CLI": str(delivery.npm_cli),
        },
        check=True,
    )
    wheel, sdist = next(artifacts.glob("ethos-*.whl")), next(artifacts.glob("ethos-*.tar.gz"))
    expected_build_identity = runtime_build_identity(root)
    assert wheel_build_identity(wheel) == expected_build_identity
    with zipfile.ZipFile(wheel) as archive:
        wheel_bytes = archive.read("ethos/data/semantic-contract/vectors.json")
    with tarfile.open(sdist, "r:gz") as archive:
        member = next(
            item
            for item in archive.getmembers()
            if item.name.endswith("tests/fixtures/semantic-contract/vectors.json")
        )
        extracted = archive.extractfile(member)
        assert extracted is not None
        sdist_bytes = extracted.read()
        identity_member = next(
            item
            for item in archive.getmembers()
            if item.name.endswith("src/ethos/data/build/identity.json")
        )
        extracted_identity = archive.extractfile(identity_member)
        assert extracted_identity is not None
        sdist_identity = json.loads(extracted_identity.read())
    assert wheel_bytes == sdist_bytes == source_bytes
    assert sdist_identity == expected_build_identity.projection()

    installed = subprocess.run(
        (
            str(runtime.python),
            "-c",
            """
import importlib.resources, json, sys, tempfile
from pathlib import Path
wheel = sys.argv[1]; sys.path.insert(0, wheel)
import ethos
from ethos.contracts.semantic import Attestation, load_commitment_file
assert str(ethos.__file__).startswith(wheel)
vectors = json.loads(
    importlib.resources.files("ethos")
    .joinpath("data/semantic-contract/vectors.json")
    .read_text()
)
with tempfile.TemporaryDirectory() as directory:
    carrier = Path(directory) / "commitment.toml"
    carrier.write_text(vectors["commitment"]["carrier_toml"])
    commitment = load_commitment_file(carrier)
attestation = Attestation.model_validate_json(vectors["attestation"]["carrier_json"])
print(json.dumps({
    "commitment": [commitment.canonical_json(), commitment.digest()],
    "attestation": [attestation.canonical_json(exclude_id=True), attestation.id],
}))
""",
            str(wheel.resolve()),
        ),
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(installed.stdout) == {
        "commitment": [commitment_vector["canonical_json"], commitment_vector["digest"]],
        "attestation": [attestation_vector["canonical_json_without_id"], attestation_vector["id"]],
    }
