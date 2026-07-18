from __future__ import annotations

from pathlib import Path


def test_repository_audit_reports_design_integrity_contract() -> None:
    from ethos.repository.audit import repository_audit

    report = repository_audit(Path.cwd(), openspec_mode="shape")
    design = report["design_integrity"]

    assert design["ok"] is True
    assert design["not_a_truth_store"] is True
    assert design["scope"] == "canonical_product_design_docs"
    assert design["required_gaps"] == []
    assert report["required_gaps"] == []


def test_repository_audit_blocks_design_truth_center_regression(tmp_path: Path) -> None:
    from ethos.repository.audit import repository_audit
    from ethos.repository.design.integrity import DESIGN_INTEGRITY_DOCS

    for relative in DESIGN_INTEGRITY_DOCS:
        source = Path.cwd() / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    product = tmp_path / "docs/governance/product-design-contract.md"
    product.write_text(
        product.read_text(encoding="utf-8") + "\nVendorTruthCenter becomes product_self.\n",
        encoding="utf-8",
    )

    report = repository_audit(tmp_path, openspec_mode="shape")
    gaps = report["design_integrity"]["required_gaps"]

    assert report["design_integrity"]["ok"] is False
    assert (
        "design_integrity_forbidden_term:docs/governance/product-design-contract.md:VendorTruthCenter"
        in gaps
    )
    assert (
        "design_integrity_forbidden_term:docs/governance/product-design-contract.md:product_self"
        in gaps
    )
    assert any(
        str(gap).startswith("design_integrity_forbidden_term:") for gap in report["required_gaps"]
    )


def test_repository_audit_blocks_vendor_center_leak(tmp_path: Path) -> None:
    from ethos.repository.audit import repository_audit
    from ethos.repository.design.integrity import DESIGN_INTEGRITY_DOCS

    for relative in DESIGN_INTEGRITY_DOCS:
        source = Path.cwd() / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    command_plane = tmp_path / "docs/reference/command-plane.md"
    command_plane.write_text(
        command_plane.read_text(encoding="utf-8") + "\nOpenAI owns the command plane.\n",
        encoding="utf-8",
    )

    report = repository_audit(tmp_path, openspec_mode="shape")
    gaps = report["design_integrity"]["required_gaps"]

    assert report["design_integrity"]["ok"] is False
    assert "design_integrity_vendor_center_leak:docs/reference/command-plane.md:OpenAI" in gaps
    assert any(
        str(gap).startswith("design_integrity_vendor_center_leak:")
        for gap in report["required_gaps"]
    )


def test_repository_audit_blocks_root_projection_pollution(tmp_path: Path) -> None:
    from ethos.repository.audit import repository_audit
    from ethos.repository.design.integrity import DESIGN_INTEGRITY_DOCS

    for relative in DESIGN_INTEGRITY_DOCS:
        source = Path.cwd() / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("vendor projection", encoding="utf-8")
    (tmp_path / ".claude" / "worktrees").mkdir(parents=True)
    recipe = tmp_path / ".ethos" / "decomp-recipes" / "retirement.py"
    recipe.parent.mkdir(parents=True)
    recipe.write_text("# scratch decomposition belongs in a Work Lane, not accepted root\n")
    plan = tmp_path / "docs" / "superpowers" / "specs" / "projection-plan.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("# host-method projection belongs outside product docs\n")

    report = repository_audit(tmp_path, openspec_mode="shape")
    gaps = report["design_integrity"]["required_gaps"]

    assert report["design_integrity"]["ok"] is False
    assert "design_integrity_forbidden_projection_path:CLAUDE.md" in gaps
    assert "design_integrity_forbidden_projection_path:.claude" in gaps
    assert "design_integrity_forbidden_projection_path:.ethos/decomp-recipes" in gaps
    assert "design_integrity_forbidden_projection_path:docs/superpowers" in gaps
    assert "design_integrity_forbidden_projection_path:CLAUDE.md" in report["required_gaps"]
    assert "design_integrity_forbidden_projection_path:.claude" in report["required_gaps"]
    assert (
        "design_integrity_forbidden_projection_path:.ethos/decomp-recipes"
        in report["required_gaps"]
    )
    assert "design_integrity_forbidden_projection_path:docs/superpowers" in report["required_gaps"]
