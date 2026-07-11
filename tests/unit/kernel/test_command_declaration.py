from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from cyclopts import App
from pydantic import ValidationError

import ethos_core.contracts.commands as command_contract
from ethos.surface.cli.quality.registry import register_declared_group
from ethos_core.contracts.commands import CommandRegistryDeclaration
from ethos_core.contracts.commands import load_command_registry_declaration

ROOT = Path(__file__).resolve().parents[3]


def test_command_declaration_compiles_command_sets_and_quality_handlers() -> None:
    declaration = load_command_registry_declaration(ROOT / "system/commands.toml")

    assert declaration.sets.public_workflow == (
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    )
    assert declaration.sets.reader_view == ("ethos orient",)
    assert declaration.sets.scorecard == ("ethos report",)
    assert declaration.sets.setup == ("ethos init", "ethos adopt", "ethos doctor")

    quality = declaration.group("quality")
    assert quality[0].name == "asset-policy"
    assert quality[-1].name == "governance-kernel"
    assert "source-budget" in {command.name for command in quality}
    assert all(command.import_path.startswith("ethos.") for command in quality)
    assert all(command.help for command in quality)


def test_command_declaration_marks_compiled_quality_report_handlers() -> None:
    declaration = load_command_registry_declaration(ROOT / "system/commands.toml")

    report_handlers = {
        command.name: command.report_handler
        for command in declaration.group("quality")
        if command.report_handler is not None
    }

    assert report_handlers["asset-policy"].provider == (
        "ethos.surface.cli.quality.core:_product_quality_profile"
    )
    assert report_handlers["asset-policy"].enforce is False
    assert report_handlers["asset-policy"].bind_root is False
    assert report_handlers["types"].provider == "ethos.adapters.gates.ty:ty_gate_report"
    assert report_handlers["types"].enforce is True
    assert report_handlers["types"].bind_root is True
    assert report_handlers["source-budget"].provider == "ethos.domain.prove:source_budget_report"
    assert report_handlers["source-budget"].enforce is True
    assert report_handlers["source-budget"].bind_root is True
    assert (
        report_handlers["no-compat"].provider
        == "ethos.repository.policy.no_compat.core:no_compat_report"
    )
    assert report_handlers["no-compat"].enforce is True
    assert report_handlers["no-compat"].bind_root is True
    assert report_handlers["product-boundary"].provider.endswith(":product_boundary_report")
    assert report_handlers["contributor-policy"].provider.endswith(":contributor_policy_report")
    assert report_handlers["enterprise-readiness"].provider.endswith(":enterprise_readiness_report")
    assert report_handlers["governance-kernel"].provider.endswith(":governance_kernel_report")
    assert "docs" not in report_handlers
    assert "coupling-audit" not in report_handlers


def test_report_handlers_are_provider_and_projection_declarations() -> None:
    handlers = [
        command.report_handler
        for command in load_command_registry_declaration(ROOT / "system/commands.toml").group(
            "quality"
        )
        if command.report_handler is not None
    ]

    assert all(handler.provider for handler in handlers)


def test_command_declaration_registers_native_cyclopts_lazy_specs() -> None:
    app = App(name="quality")
    declaration = load_command_registry_declaration(ROOT / "system/commands.toml")

    registered = register_declared_group(app, "quality")

    assert registered == len(declaration.group("quality"))
    assert {command.name for command in declaration.group("quality")} <= set(app)
    assert register_declared_group(app, "quality") == 0

    root = App(name="ethos")
    assert register_declared_group(root, "root") == 14
    assert {command.name for command in declaration.group("root")} <= set(root)


def test_command_declaration_is_frozen_strict_and_rejects_duplicate_names() -> None:
    declaration = load_command_registry_declaration(ROOT / "system/commands.toml")
    with pytest.raises(ValidationError):
        declaration.commands[0].name = "changed"  # type: ignore[misc]

    payload = declaration.model_dump()
    payload["commands"] = [*payload["commands"], payload["commands"][0]]
    with pytest.raises(ValidationError, match="duplicate command name"):
        CommandRegistryDeclaration.model_validate(payload)


def test_command_declaration_falls_back_outside_a_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert load_command_registry_declaration(tmp_path / "missing.toml").id == (
        "ethos-command-registry"
    )


def test_command_declaration_default_searches_package_parents_then_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with TemporaryDirectory() as directory:
        isolated = Path(directory)
        nested_contract = isolated / "src/ethos_core/contracts/commands.py"
        repository = isolated / "system/commands.toml"
        outside = isolated / "outside"
        repository.parent.mkdir()
        outside.mkdir()
        repository.write_bytes((ROOT / "system/commands.toml").read_bytes())
        monkeypatch.chdir(outside)
        monkeypatch.setattr(command_contract, "__file__", str(nested_contract))

        assert load_command_registry_declaration().id == "ethos-command-registry"
        repository.unlink()
        assert load_command_registry_declaration().id == "ethos-command-registry"
