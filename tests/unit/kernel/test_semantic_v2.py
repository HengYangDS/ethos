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

from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import load_commitment_file
from tools.ci.delivery.pipeline import DeliveryPipeline
from tools.ci.toolchain.environment import ProjectRuntime

_JSON_SCALAR = (
    st.none()
    | st.booleans()
    | st.integers(
        min_value=-9_007_199_254_740_991,
        max_value=9_007_199_254_740_991,
    )
    | st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=24)
)
_JSON_OBJECT = st.recursive(
    _JSON_SCALAR,
    lambda children: (
        st.lists(children, max_size=4)
        | st.dictionaries(
            st.text(
                alphabet=st.characters(blacklist_categories=("Cs",)),
                min_size=1,
                max_size=12,
            ),
            children,
            max_size=4,
        )
    ),
    max_leaves=12,
).flatmap(lambda value: st.just(value) if isinstance(value, dict) else st.just({"value": value}))


def _commitment_payload() -> dict[str, object]:
    return {
        "schema_version": 2,
        "id": "change:model-promotion-successor",
        "intent": "Adopt one selected input without expanding its predecessor.",
        "subjects": ["repository:ethos"],
        "scope": ["src/ethos/contracts/semantic.py"],
        "invariants": ["selection_never_mints_authority"],
        "acceptance": ["selected_input_is_bound"],
        "risks": ["destructive_cutover"],
        "authority_refs": ["AGENTS.md"],
        "predecessors": ["1" * 64],
        "selected_attestations": ["2" * 64],
        "dependencies": [
            {
                "kind": "dependency:requires",
                "target": "commitment:repository:ethos",
                "attributes": {"strength": 1},
            }
        ],
        "hypotheses": [
            {
                "id": "hypothesis:bounded-input",
                "kind": "hypothesis:causal",
                "body": {"proposition": "A successor preserves bounded closure."},
            }
        ],
        "falsifiers": [
            {
                "id": "falsifier:active-change-expanded",
                "hypothesis_id": "hypothesis:bounded-input",
                "kind": "observation:repository",
                "body": {"path": "openspec/changes/model-promotion/tasks.md"},
            }
        ],
        "experiment_protocols": [
            {
                "id": "protocol:successor-selection",
                "hypothesis_ids": ["hypothesis:bounded-input"],
                "kind": "experiment:repository",
                "body": {"steps": ["record", "select", "adopt"]},
            }
        ],
    }


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


def test_commitment_v2_accepts_existing_repository_uuid_identity() -> None:
    payload = _commitment_payload()
    repository_id = "repository:2454ddfb-3395-497b-b07c-416ac2e3a0ad"

    commitment = Commitment.model_validate(
        payload | {"id": repository_id, "subjects": [repository_id]}
    )

    assert commitment.id == repository_id


@pytest.mark.parametrize("field", tuple(_commitment_payload()))
def test_commitment_v2_rejects_every_omitted_identity_field(field: str) -> None:
    payload = _commitment_payload()
    del payload[field]

    with pytest.raises(ValidationError):
        Commitment.model_validate(payload)


def test_commitment_v2_loader_rejects_contextual_subject_alias(tmp_path: Path) -> None:
    payload = _commitment_payload()
    payload["subjects"] = ["repository:self"]
    carrier = tmp_path / "commitment.toml"
    carrier.write_text(tomli_w.dumps(payload), encoding="utf-8")

    with pytest.raises(ValidationError, match="commitment_string_value_invalid"):
        load_commitment_file(carrier)


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("intent", " ", "commitment_string_value_invalid"),
        ("subjects", [" "], "commitment_string_value_invalid"),
        ("invariants", [" "], "commitment_string_value_invalid"),
        ("acceptance", [" "], "commitment_string_value_invalid"),
        ("risks", [" "], "commitment_string_value_invalid"),
        ("authority_refs", [" "], "commitment_string_value_invalid"),
        ("scope", [" "], "change_scope_invalid"),
        (
            "dependencies",
            [{"kind": "dependency:requires", "target": " ", "attributes": {}}],
            "commitment_string_value_invalid",
        ),
    ],
)
def test_commitment_v2_rejects_blank_semantic_strings(
    field: str, value: object, error: str
) -> None:
    with pytest.raises(ValidationError, match=error):
        Commitment.model_validate(_commitment_payload() | {field: value})


def test_canonical_json_rejects_non_string_keys_before_projection() -> None:
    payload = _commitment_payload()
    payload["dependencies"] = [
        {
            "kind": "dependency:requires",
            "target": "commitment:invalid-key",
            "attributes": {1: "first", "1": "second"},
        }
    ]

    with pytest.raises((TypeError, ValidationError), match="object_key_invalid"):
        Commitment.model_validate(payload)


def test_commitment_v2_uses_declared_unicode_orders() -> None:
    payload = _commitment_payload()
    payload["subjects"] = ["repository:\ue000", "repository:\U00010000"]
    payload["dependencies"] = [
        {
            "kind": "dependency:requires",
            "target": "commitment:unicode-order",
            "attributes": {"\U00010000": 1, "\ue000": 2},
        }
    ]

    commitment = Commitment.model_validate(payload)

    assert '"attributes":{"\U00010000":1,"\ue000":2}' in commitment.canonical_json()
    with pytest.raises(ValidationError, match="semantic_collection_order_invalid"):
        Commitment.model_validate(payload | {"subjects": list(reversed(payload["subjects"]))})


def test_commitment_v2_rejects_ambiguous_or_dangling_hypothesis_graph() -> None:
    payload = _commitment_payload()
    duplicate = dict(payload["hypotheses"][0])
    duplicate["body"] = {"proposition": "A different proposition."}

    with pytest.raises(ValidationError, match="commitment_hypothesis_id_duplicate"):
        Commitment.model_validate(payload | {"hypotheses": [*payload["hypotheses"], duplicate]})

    dangling_falsifier = dict(payload["falsifiers"][0])
    dangling_falsifier["hypothesis_id"] = "hypothesis:missing"
    with pytest.raises(ValidationError, match="commitment_hypothesis_reference_missing"):
        Commitment.model_validate(payload | {"falsifiers": [dangling_falsifier]})

    dangling_protocol = dict(payload["experiment_protocols"][0])
    dangling_protocol["hypothesis_ids"] = ["hypothesis:missing"]
    with pytest.raises(ValidationError, match="commitment_hypothesis_reference_missing"):
        Commitment.model_validate(payload | {"experiment_protocols": [dangling_protocol]})


def test_attestation_v2_round_trips_unknown_payload_and_relation() -> None:
    first = Attestation.issue(_attestation_payload())
    restored = Attestation.model_validate_json(first.canonical_json())

    assert restored == first
    assert restored.payload.kind == "input:feedback"
    assert restored.relations[0].kind == "relation:selected-for"
    assert restored.mints_authority is False


@settings(max_examples=40, deadline=None)
@given(body=_JSON_OBJECT)
def test_attestation_v2_unknown_payload_round_trip_preserves_identity(body: object) -> None:
    issued = Attestation.issue(
        _attestation_payload() | {"payload": {"kind": "input:future-feedback", "body": body}}
    )

    restored = Attestation.model_validate_json(issued.canonical_json())

    assert restored == issued
    assert restored.id == issued.id


def test_attestation_v2_rejects_implicit_or_authorizing_values() -> None:
    payload = _attestation_payload()
    del payload["facts_digest"]
    with pytest.raises(ValidationError):
        Attestation.issue(payload)

    with pytest.raises(ValidationError):
        Attestation.issue(_attestation_payload() | {"mints_authority": True})

    unbound = _attestation_payload() | {
        "relations": [],
        "evidence_refs": [],
        "commitment_digest": None,
    }
    with pytest.raises(ValidationError, match="attestation_binding_missing"):
        Attestation.issue(unbound)


def test_attestation_v2_rejects_duplicate_relation_identity() -> None:
    payload = _attestation_payload()
    duplicate = dict(payload["relations"][0])
    duplicate["attributes"] = {"different": True}

    with pytest.raises(ValidationError, match="attestation_relation_identity_duplicate"):
        Attestation.issue(payload | {"relations": [*payload["relations"], duplicate]})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("verifier", " "),
        ("subject", " "),
        ("advisories", [" "]),
        ("evidence_refs", [" "]),
    ],
)
def test_attestation_v2_rejects_blank_semantic_strings(field: str, value: object) -> None:
    with pytest.raises(ValidationError, match="commitment_string_value_invalid"):
        Attestation.issue(_attestation_payload() | {field: value})


def test_attestation_relation_can_target_attestation_identity() -> None:
    target = Attestation.issue(_attestation_payload())
    payload = _attestation_payload()
    payload["relations"] = [
        {
            "kind": "relation:derived-from",
            "target_kind": "semantic:attestation",
            "target_id": target.id,
            "attributes": {},
        }
    ]

    issued = Attestation.issue(payload)

    assert issued.relations[0].target_id == target.id


def test_semantic_json_reader_rejects_duplicate_object_keys() -> None:
    raw = '{"schema_version":2,"schema_version":2}'

    with pytest.raises(ValueError, match="semantic_object_key_duplicate"):
        Commitment.model_validate_json(raw)


@pytest.mark.parametrize(
    "raw",
    [
        lambda canonical: b" " + canonical,
        lambda _canonical: json.dumps(
            _commitment_payload(), ensure_ascii=False, separators=(",", ":")
        ).encode(),
        lambda canonical: canonical + b"\n",
    ],
    ids=("leading-whitespace", "key-order", "trailing-newline"),
)
def test_semantic_json_reader_rejects_noncanonical_bytes(raw) -> None:
    canonical = Commitment.model_validate(_commitment_payload()).canonical_json().encode()

    with pytest.raises(ValueError, match="semantic_json_noncanonical"):
        Commitment.model_validate_json(raw(canonical))


def test_semantic_json_reader_strict_false_cannot_admit_noncanonical_bytes() -> None:
    canonical = Commitment.model_validate(_commitment_payload()).canonical_json().encode()

    with pytest.raises(ValueError, match="semantic_json_noncanonical"):
        Commitment.model_validate_json(canonical + b"\n", strict=False)


def test_semantic_json_reader_normalizes_unsupported_value_errors() -> None:
    canonical = Commitment.model_validate(_commitment_payload()).canonical_json()
    unsupported = canonical.replace('"strength":1', '"strength":1.5').encode()

    with pytest.raises(ValueError, match="semantic_json_value_invalid"):
        Commitment.model_validate_json(unsupported)


def test_semantic_v2_golden_vectors_are_exact_in_source_wheel_and_sdist(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[3]
    vector_path = root / "tests/fixtures/semantic-v2/vectors.json"
    source_bytes = vector_path.read_bytes()
    vectors = json.loads(source_bytes)
    assert vectors["schema_version"] == 1
    commitment_vector = vectors["commitment"]
    commitment_path = tmp_path / "commitment.toml"
    commitment_path.write_text(commitment_vector["carrier_toml"], encoding="utf-8")
    commitment = load_commitment_file(commitment_path)
    attestation_vector = vectors["attestation"]
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
    assert force_include["tests/fixtures/semantic-v2/vectors.json"] == (
        "ethos/data/semantic-v2/vectors.json"
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
    wheel = next(artifacts.glob("ethos-*.whl"))
    sdist = next(artifacts.glob("ethos-*.tar.gz"))
    with zipfile.ZipFile(wheel) as archive:
        wheel_bytes = archive.read("ethos/data/semantic-v2/vectors.json")
    with tarfile.open(sdist, "r:gz") as archive:
        member = next(
            item
            for item in archive.getmembers()
            if item.name.endswith("tests/fixtures/semantic-v2/vectors.json")
        )
        extracted = archive.extractfile(member)
        assert extracted is not None
        sdist_bytes = extracted.read()
    assert wheel_bytes == sdist_bytes == source_bytes

    installed = subprocess.run(
        (
            str(runtime.python),
            "-c",
            """
import importlib.resources
import json
import sys
import tempfile
from pathlib import Path

wheel = sys.argv[1]
sys.path.insert(0, wheel)
import ethos
from ethos.contracts.semantic import Attestation, load_commitment_file

assert str(ethos.__file__).startswith(wheel)
vectors = json.loads(
    importlib.resources.files("ethos").joinpath("data/semantic-v2/vectors.json").read_text()
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
        "attestation": [
            attestation_vector["canonical_json_without_id"],
            attestation_vector["id"],
        ],
    }
