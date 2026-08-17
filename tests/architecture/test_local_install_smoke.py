from __future__ import annotations

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import tools.ci.delivery.pipeline as delivery_pipeline
import tools.ci.local_install_smoke as local_install_smoke
from ethos.contracts.semantic import load_commitment_file
from tools.ci.delivery.pipeline import DeliveryPipeline

if TYPE_CHECKING:
    import nox

    from tools.ci.toolchain.environment import ProjectRuntime

ROOT = Path(__file__).resolve().parents[2]


def test_package_gate_order_and_offline_contract_have_one_machine_owner() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    full = declaration["proof_sets"]["full"]
    gates = {item["id"]: item for item in declaration["gates"]}
    smoke = gates["local-install-smoke"]
    assert full.count("local-install-smoke") == 1
    assert full.index("build") < full.index("local-install-smoke")
    assert smoke["depends_on"] == ["build"]
    assert smoke["network_policy"] == "offline"
    assert smoke["writes_files"] is True


def test_package_only_runtime_behavior_remains_owned_by_install_smoke() -> None:
    owner = (ROOT / "tools/ci/local_install_smoke.py").read_text(encoding="utf-8")
    assert "build/runtime/work/local-install-smoke" in owner
    assert '"external_governance_available": False' in owner
    assert '"hosted_ci_status_claimed": False' in owner
    assert '"publish", "--proposal"' in owner


def test_install_smoke_prepares_frozen_supply_before_offline_install(
    monkeypatch,
) -> None:
    events: list[object] = []
    session = cast("nox.Session", object())
    monkeypatch.setattr(delivery_pipeline, "prepare_supply", lambda: events.append("supply"))
    monkeypatch.setattr(
        delivery_pipeline,
        "run_install_smoke",
        lambda observed: events.append(("install", observed)),
    )

    DeliveryPipeline(
        runtime=cast("ProjectRuntime", object()),
        node=Path("node"),
        npm_cli=Path("npm-cli.js"),
    ).prove_install(session)

    assert events == ["supply", ("install", session)]


def test_packaged_vector_derives_a_complete_strict_v2_commitment(
    monkeypatch,
    tmp_path: Path,
) -> None:
    vectors = (ROOT / "tests/fixtures/semantic-v2/vectors.json").read_text(encoding="utf-8")
    monkeypatch.setattr(local_install_smoke, "_run", lambda *_args, **_kwargs: vectors)

    carrier = tmp_path / "commitment.toml"
    carrier.write_text(
        local_install_smoke.commitment_carrier_from_packaged_vector(
            Path("ethos.whl"),
            Path("python"),
            commitment_id="change:install-smoke",
            intent="Prove the installed package carrier.",
            subjects=("repository:install-smoke",),
            scope=("README.md",),
        ),
        encoding="utf-8",
    )

    commitment = load_commitment_file(carrier)
    assert commitment.id == "change:install-smoke"
    assert commitment.dependencies
    assert commitment.hypotheses
    assert commitment.falsifiers
    assert commitment.experiment_protocols


def test_install_smoke_materializes_the_adopted_terminal_v1_reader_shape(
    tmp_path: Path,
) -> None:
    adopter = tmp_path / "adopter"
    adopter.mkdir()

    local_install_smoke.write_adopted_reader_compatibility(adopter)

    commitment = tomllib.loads((adopter / ".ethos/commitment.toml").read_text(encoding="utf-8"))
    workspace = tomllib.loads((adopter / ".ethos/workspace.toml").read_text(encoding="utf-8"))
    assert "schema_version" not in commitment
    assert commitment["id"] == "repository:installed-cli-adopter"
    assert commitment["scope"] == ["**"]
    assert workspace["branch_roles"]["transitions"] == [
        {
            "id": "accepted-to-release",
            "source_role": "accepted_root",
            "target_role": "release_root",
            "capability": "repository.release",
            "required_gates": [],
            "required_evidence": ["proof:execution"],
            "coupled_with": "",
        }
    ]


def test_install_smoke_adopted_reader_has_complete_declared_branch_topology(
    tmp_path: Path,
) -> None:
    adopter = tmp_path / "adopter"

    local_install_smoke.initialize_adopted_reader(adopter)

    heads = {
        branch: local_install_smoke._run(  # noqa: SLF001
            "git", "rev-parse", branch, cwd=adopter
        )
        for branch in ("main", "dev", "candidate/dev")
    }
    assert len(set(heads.values())) == 1
