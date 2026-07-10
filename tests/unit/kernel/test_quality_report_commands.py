from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

import ethos.surface.cli.quality.core as quality_core
from ethos.surface.cli.boundary import product as boundary_product
from ethos.surface.cli.boundary import readiness as boundary_readiness
from ethos.surface.cli.quality.cutover import core as cutover_core
from ethos.surface.cli.quality.reporting import ReportCommandSpec
from ethos.surface.cli.quality.reporting import ReportHandlerSpec
from ethos.surface.cli.quality.reporting import advisory_state
from ethos.surface.cli.quality.reporting import build_report_result
from ethos.surface.cli.quality.reporting import compile_report_commands
from ethos.surface.cli.quality.reporting import conditional_actions
from ethos.surface.cli.quality.reporting import constant_actions
from ethos.surface.cli.quality.reporting import count_at
from ethos.surface.cli.quality.reporting import count_of
from ethos.surface.cli.quality.reporting import declared_report_handler
from ethos.surface.cli.quality.reporting import emit_report_command
from ethos.surface.cli.quality.reporting import field_data
from ethos.surface.cli.quality.reporting import field_summary
from ethos.surface.cli.quality.reporting import head_bound_report
from ethos.surface.cli.quality.reporting import module_report
from ethos.surface.cli.quality.reporting import path_value
from ethos.surface.cli.quality.reporting import payload_report
from ethos.surface.cli.quality.reporting import project_summary
from ethos_core.contracts.commands import CommandDeclaration
from ethos_core.contracts.commands import ReportHandlerDeclaration


def test_report_command_spec_builds_ethos_result_from_report() -> None:
    spec = ReportCommandSpec(
        command="quality sample",
        report=lambda _root: {
            "ok": True,
            "state": "clean",
            "summary": {"item_count": 2},
            "required_gaps": [],
            "payload": "value",
        },
    )

    result = build_report_result(spec, Path("/repo"))

    assert result.command == "quality sample"
    assert result.ok is True
    assert result.state == "clean"
    assert result.summary == {"item_count": 2}
    assert result.required_gaps == ()
    assert result.data["payload"] == "value"


def test_report_command_spec_supports_summary_projection_and_next_actions() -> None:
    spec = ReportCommandSpec(
        command="quality blocked",
        report=lambda _root: {
            "ok": False,
            "state": "blocked",
            "required_gaps": ["sample_gap"],
            "count": 3,
        },
        summary=lambda report: {"count": report["count"]},
        next_actions=constant_actions("fix sample_gap"),
    )

    result = build_report_result(spec, Path("/repo"))

    assert result.ok is False
    assert result.state == "blocked"
    assert result.summary == {"count": 3}
    assert result.required_gaps == ("sample_gap",)
    assert result.next_actions == ("fix sample_gap",)


def test_report_command_spec_supports_field_summary_projection() -> None:
    spec = ReportCommandSpec(
        command="quality fields",
        report=lambda _root: {
            "ok": True,
            "state": "clean",
            "item_count": 4,
            "warning_count": 0,
        },
        summary=field_summary("item_count", "warning_count"),
    )

    result = build_report_result(spec, Path("/repo"))

    assert result.summary == {"item_count": 4, "warning_count": 0}


def test_report_command_spec_supports_conditional_next_actions() -> None:
    blocked = ReportCommandSpec(
        command="quality conditional",
        report=lambda _root: {"ok": False, "required_gaps": ["sample_gap"]},
        next_actions=conditional_actions(
            when_blocked="fix sample_gap",
            when_clean="keep monitoring",
        ),
    )
    clean = ReportCommandSpec(
        command="quality conditional",
        report=lambda _root: {"ok": True, "required_gaps": []},
        next_actions=conditional_actions(
            when_blocked="fix sample_gap",
            when_clean="keep monitoring",
        ),
    )

    assert build_report_result(blocked, Path("/repo")).next_actions == ("fix sample_gap",)
    assert build_report_result(clean, Path("/repo")).next_actions == ("keep monitoring",)


def test_emit_report_command_delegates_built_result_to_emit_function() -> None:
    emitted = []
    spec = ReportCommandSpec(
        command="quality emitted",
        report=lambda _root: {
            "ok": True,
            "state": "clean",
            "summary": {"item_count": 1},
        },
    )

    emit_report_command(spec, Path("/repo"), emit_func=emitted.append)

    assert len(emitted) == 1
    assert emitted[0].command == "quality emitted"
    assert emitted[0].summary == {"item_count": 1}


def test_project_summary_composes_path_count_and_default_projections() -> None:
    summary = project_summary(
        item_count=count_of("items"),
        nested_count=count_at("nested", "items"),
        nested_value=path_value("nested", "value"),
        missing_flag=path_value("nested", "missing", default=False),
        non_mapping_fallback=path_value("not_a_mapping", "value", default="fallback"),
    )

    assert summary(
        {
            "items": ["a", "b"],
            "nested": {"items": (1,), "value": "kept"},
            "not_a_mapping": [],
        }
    ) == {
        "item_count": 2,
        "nested_count": 1,
        "nested_value": "kept",
        "missing_flag": False,
        "non_mapping_fallback": "fallback",
    }


def test_payload_report_wraps_payload_for_declarative_specs() -> None:
    loader = payload_report(lambda root: {"root": root.name, "items": ["x"]})

    assert loader(Path("/repo")) == {
        "ok": True,
        "state": "clean",
        "payload": {"root": "repo", "items": ["x"]},
    }


def test_field_data_and_advisory_state_capture_common_report_shapes() -> None:
    data = field_data("payload")({"payload": {"kept": True}, "ignored": False})
    state = advisory_state("advisory_gaps")

    assert data == {"kept": True}
    ok = bool(1)
    blocked = bool(0)

    assert state({"advisory_gaps": ["warn"]}, ok) == "advisory"
    assert state({"advisory_gaps": []}, ok) == "clean"
    assert state({"advisory_gaps": ["warn"]}, blocked) == "blocked"


def test_report_command_spec_supports_data_projection() -> None:
    spec = ReportCommandSpec(
        command="quality projected",
        report=lambda _root: {
            "ok": True,
            "state": "clean",
            "summary": {"item_count": 1},
            "payload": {"kept": True},
            "internal": "hidden",
        },
        data=lambda report: report["payload"],
    )

    result = build_report_result(spec, Path("/repo"))

    assert result.data == {"kept": True}


def test_head_bound_report_passes_current_head_to_loader() -> None:
    seen: dict[str, str] = {}

    def report(root: Path, *, current_head: str = "") -> dict[str, object]:
        seen["root"] = root.as_posix()
        seen["head"] = current_head
        return {"ok": True, "state": "clean"}

    loader = head_bound_report(report, current_head=lambda root: f"head:{root.name}")

    assert loader(Path("/repo"))["state"] == "clean"
    assert seen == {"root": "/repo", "head": "head:repo"}


def test_simple_quality_commands_are_compiled_from_report_specs() -> None:
    expected_functions = {
        "asset_policy",
        "quality_types",
        "docs_topology",
        "proof_policy",
        "tool_profiles_command",
        "coverage",
        "docstrings",
        "code_size",
        "module_layout",
        "generated_artifacts",
        "command_surface",
        "projection_drift",
        "schemas",
        "standards",
        "gates",
        "release",
        "release_policy",
        "sbom",
        "command_registry",
        "evidence_freshness",
        "claims",
        "docs_registry",
        "command_examples",
    }

    assert set(quality_core.REPORT_COMMANDS) == expected_functions
    for function_name, (
        command_name,
        spec,
        _enforce,
        _bind_root,
    ) in quality_core.REPORT_COMMANDS.items():
        assert getattr(quality_core, function_name).__doc__
        assert isinstance(spec, ReportCommandSpec)
        assert spec.command == f"quality {command_name}"


def test_quality_report_commands_are_compiled_from_command_declaration() -> None:
    registry = quality_core.REPORT_COMMANDS

    assert registry["asset_policy"][1] is quality_core.ASSET_POLICY_COMMAND
    assert registry["quality_types"][1] is quality_core.TYPES_COMMAND
    assert registry["quality_types"][2:] == (True, True)
    assert registry["claims"][1] is quality_core.CLAIMS_COMMAND
    assert registry["claims"][2:] == (False, True)

    source = Path("packages/ethos/src/ethos/surface/cli/quality/core.py").read_text(
        encoding="utf-8"
    )
    report_table = source[source.index("REPORT_COMMANDS = ") :]
    assert "compile_report_commands(" in report_table
    assert 'asset_policy": (' not in report_table
    assert 'quality_types": (' not in report_table


def test_compile_report_commands_reuses_command_registry_metadata() -> None:
    declarations = tuple(
        command
        for command in quality_core.load_command_registry_declaration().group("quality")
        if command.name in {"asset-policy", "types"}
    )
    registry = compile_report_commands(
        declarations=declarations,
        specs={
            "ASSET_POLICY_COMMAND": quality_core.ASSET_POLICY_COMMAND,
            "TYPES_COMMAND": quality_core.TYPES_COMMAND,
        },
    )

    assert registry == {
        "asset_policy": (
            "asset-policy",
            quality_core.ASSET_POLICY_COMMAND,
            False,
            False,
        ),
        "quality_types": (
            "types",
            quality_core.TYPES_COMMAND,
            True,
            True,
        ),
    }


def test_compile_report_commands_can_scope_to_one_lazy_module() -> None:
    declarations = quality_core.load_command_registry_declaration().group("quality")

    registry = compile_report_commands(
        declarations=declarations,
        specs={
            "NO_COMPAT_COMMAND": cutover_core.NO_COMPAT_COMMAND,
            "PRODUCT_BOUNDARY_COMMAND": boundary_product.PRODUCT_BOUNDARY_COMMAND,
        },
        import_path_prefix="ethos.surface.cli.quality.cutover.core:",
    )

    assert registry == {
        "no_compat": (
            "no-compat",
            cutover_core.NO_COMPAT_COMMAND,
            True,
            True,
        )
    }


def test_compile_report_commands_rejects_missing_declared_spec() -> None:
    declaration = CommandDeclaration(
        name="sample",
        group="quality",
        import_path="ethos.surface.cli.quality.core:sample",
        help="Sample.",
        report_handler=ReportHandlerDeclaration(spec="MISSING_COMMAND"),
    )

    with pytest.raises(KeyError, match="MISSING_COMMAND"):
        compile_report_commands(declarations=(declaration,), specs={})


def test_declared_report_handler_uses_command_declaration_metadata() -> None:
    handler = declared_report_handler(
        module_name="ethos.surface.cli.quality.cutover.core",
        function_name="no_compat",
        spec_name="NO_COMPAT_COMMAND",
        spec=cutover_core.NO_COMPAT_COMMAND,
    )

    assert handler.__name__ == "no_compat"
    assert handler.__module__ == "ethos.surface.cli.quality.cutover.core"
    assert handler.__doc__ == "Check production source for compatibility residue."


def test_declared_report_handler_rejects_spec_mismatch() -> None:
    with pytest.raises(ValueError, match="report handler spec mismatch"):
        declared_report_handler(
            module_name="ethos.surface.cli.quality.cutover.core",
            function_name="no_compat",
            spec_name="WRONG_COMMAND",
            spec=cutover_core.NO_COMPAT_COMMAND,
        )


def test_declared_report_handler_rejects_missing_command_declaration() -> None:
    with pytest.raises(KeyError, match="command declaration missing"):
        declared_report_handler(
            module_name="ethos.surface.cli.quality.cutover.core",
            function_name="missing_command",
            spec_name="NO_COMPAT_COMMAND",
            spec=cutover_core.NO_COMPAT_COMMAND,
        )


def test_declared_report_handler_rejects_command_without_report_handler() -> None:
    with pytest.raises(KeyError, match="report handler declaration missing"):
        declared_report_handler(
            module_name="ethos.surface.cli.quality.core",
            function_name="markdown_links",
            spec_name="NO_COMPAT_COMMAND",
            spec=cutover_core.NO_COMPAT_COMMAND,
        )


def test_declared_report_handler_rejects_command_name_mismatch() -> None:
    mismatched_spec = ReportCommandSpec(
        command="quality wrong-name",
        report=lambda _root: {"ok": True},
    )

    with pytest.raises(ValueError, match="report command mismatch"):
        declared_report_handler(
            module_name="ethos.surface.cli.quality.cutover.core",
            function_name="no_compat",
            spec_name="NO_COMPAT_COMMAND",
            spec=mismatched_spec,
        )


def test_release_attestation_uses_report_spec_without_handwritten_result() -> None:
    source = Path("packages/ethos/src/ethos/surface/cli/quality/core.py").read_text(
        encoding="utf-8"
    )
    start = source.index("def release_attestation_command(")
    next_function = source.find("\ndef ", start + 1)
    body = source[start:] if next_function == -1 else source[start:next_function]

    assert "emit_report_command(" in body
    assert "ReportCommandSpec(" in body
    assert "EthosResult(" not in body


@pytest.mark.parametrize(
    ("module_path", "function_name", "spec_name"),
    [
        (
            "packages/ethos/src/ethos/surface/cli/quality/cutover/core.py",
            "no_compat",
            "NO_COMPAT_COMMAND",
        ),
        (
            "packages/ethos/src/ethos/surface/cli/boundary/product.py",
            "product_boundary",
            "PRODUCT_BOUNDARY_COMMAND",
        ),
        (
            "packages/ethos/src/ethos/surface/cli/boundary/product.py",
            "contributor_policy",
            "CONTRIBUTOR_POLICY_COMMAND",
        ),
        (
            "packages/ethos/src/ethos/surface/cli/boundary/readiness.py",
            "enterprise_readiness",
            "ENTERPRISE_READINESS_COMMAND",
        ),
        (
            "packages/ethos/src/ethos/surface/cli/boundary/readiness.py",
            "governance_kernel",
            "GOVERNANCE_KERNEL_COMMAND",
        ),
    ],
)
def test_boundary_quality_commands_use_declarative_report_handler(
    module_path: str,
    function_name: str,
    spec_name: str,
) -> None:
    source = Path(module_path).read_text(encoding="utf-8")

    assert f"{spec_name} = ReportCommandSpec(" in source
    assert f"{function_name} = declared_report_handler(" in source
    assert "EthosResult(" not in source
    assert "def " + function_name not in source


def test_report_command_spec_is_frozen_pydantic_contract() -> None:
    spec = ReportCommandSpec(command="quality immutable", report=lambda _root: {"ok": True})

    with pytest.raises(ValidationError, match="frozen_instance"):
        spec.command = "quality changed"  # type: ignore[misc]


def test_report_handler_spec_is_frozen_pydantic_contract() -> None:
    spec = ReportHandlerSpec(
        report=ReportCommandSpec(command="quality immutable", report=lambda _root: {"ok": True}),
        enforce=False,
        bind_root=True,
        doc="Immutable.",
    )

    with pytest.raises(ValidationError, match="frozen_instance"):
        spec.doc = "Changed."  # type: ignore[misc]


def test_report_command_spec_rejects_non_callable_report() -> None:
    with pytest.raises(ValidationError):
        ReportCommandSpec(command="quality invalid", report="not-callable")  # type: ignore[arg-type]


def test_module_report_resolves_latest_namespace_binding() -> None:
    calls: list[str] = []
    namespace: dict[str, object] = {"report": lambda _root: {"ok": True, "state": "first"}}
    loader = module_report(namespace, "report")
    namespace["report"] = lambda _root: (
        calls.append("second")
        or {
            "ok": True,
            "state": "second",
        }
    )

    assert loader(Path("/repo"))["state"] == "second"
    assert calls == ["second"]


def test_module_report_rejects_non_callable_namespace_binding() -> None:
    loader = module_report({"report": "not-callable"}, "report")

    with pytest.raises(TypeError, match="report binding is not callable: report"):
        loader(Path("/repo"))


def test_imported_boundary_command_specs_are_declarative_contracts() -> None:
    assert cutover_core.no_compat.__doc__ == "Check production source for compatibility residue."
    assert boundary_product.product_boundary.__doc__ == (
        "Audit product and release-visible historical surfaces for boundary leaks."
    )
    assert boundary_product.contributor_policy.__doc__ == (
        "Audit organization-native contributor, role, and automation identity policy."
    )
    assert boundary_readiness.enterprise_readiness.__doc__ == (
        "Audit enterprise-neutral readiness across product boundary, docs, identity, and release."
    )
    assert boundary_readiness.governance_kernel.__doc__ == (
        "Audit the single kernel shared by product and adopted repositories."
    )
