from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

import ethos_core.contracts.gates as gates_contract
from ethos_core.contracts.gates import GateRegistryDeclaration
from ethos_core.contracts.gates import load_gate_registry_declaration

ROOT = Path(__file__).resolve().parents[3]


def test_gate_declaration_compiles_runtime_quality_and_proof_sets() -> None:
    declaration = load_gate_registry_declaration(ROOT / "system/gates.toml")

    runtime = declaration.registry("runtime")
    bound_runtime = declaration.registry("runtime", python_executable="/python")
    quality = declaration.registry("quality")

    assert "source-budget" in runtime
    assert "source-budget" in quality
    assert runtime["repository-audit"].resolved_command("/python") == (
        "/python",
        "-m",
        "ethos.cli",
        "audit",
        "--mode",
        "shape",
        "--json",
    )
    assert bound_runtime["repository-audit"].command[0] == "/python"
    assert runtime["repository-audit"].to_dict()["command"][0] == "{python}"
    assert quality["module-layout"].depends_on == ("python-lint",)
    assert runtime["module-layout"].depends_on == ()
    assert declaration.proof_sets.product_default[0] == "repository-audit"
    assert declaration.proof_sets.product_full[-1] == "npm-pack"
    assert set(declaration.proof_sets.product_default) <= set(declaration.proof_sets.product_full)


def test_gate_declaration_models_are_frozen_and_strict(tmp_path: Path) -> None:
    declaration = load_gate_registry_declaration(ROOT / "system/gates.toml")

    with pytest.raises(ValidationError):
        declaration.gates[0].id = "changed"  # type: ignore[misc]

    invalid = tmp_path / "gates.toml"
    invalid.write_text(
        """id = "invalid"
schema_version = 1
unknown = true

[proof_sets]
product_default = []
product_full = []
adopter_default = []
""",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_gate_registry_declaration(invalid)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda payload: payload["gates"].append(dict(payload["gates"][0])),
            "duplicate gate id",
        ),
        (
            lambda payload: payload["gates"][0].update(depends_on=["missing"]),
            "unavailable gate dependency",
        ),
        (
            lambda payload: payload["proof_sets"]["product_default"].append("import-boundaries"),
            "product full missing default",
        ),
        (
            lambda payload: payload["proof_sets"]["product_default"].append("missing"),
            "unknown proof gate",
        ),
        (
            lambda payload: payload["proof_sets"]["product_default"].append(
                payload["proof_sets"]["product_default"][0]
            ),
            "duplicate proof gate",
        ),
    ],
)
def test_gate_declaration_rejects_invalid_references(mutate, message: str) -> None:
    payload = load_gate_registry_declaration(ROOT / "system/gates.toml").model_dump()
    payload["gates"] = list(payload["gates"])
    payload["proof_sets"] = {key: list(value) for key, value in payload["proof_sets"].items()}
    mutate(payload)

    with pytest.raises(ValidationError, match=message):
        GateRegistryDeclaration.model_validate(payload)


def test_gate_declaration_uses_repository_default_and_packaged_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(ROOT)
    assert load_gate_registry_declaration().id == "gate-registry"

    monkeypatch.chdir(tmp_path)
    assert load_gate_registry_declaration().id == "gate-registry"
    assert load_gate_registry_declaration(tmp_path / "missing.toml").id == "gate-registry"

    monkeypatch.setattr(gates_contract, "DECLARATION_PATH", Path("absent.toml"))
    monkeypatch.setattr(gates_contract, "__file__", str(tmp_path / "isolated" / "gates.py"))
    assert gates_contract._default_declaration_path() == Path("absent.toml")
