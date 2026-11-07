"""Executable product boundaries not duplicated by policy and schema gates."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ethos.adapters.repo.content.observation import observed_document_origins
from ethos.contracts.admission import ethos_command_is_readonly
from ethos.repository.policy.boundary.product import product_boundary_report
from ethos.repository.policy.references.closure import repository_semantic_closure

ROOT = Path(__file__).resolve().parents[2]
COMMIT_ADMISSION_OWNER = ROOT / "src/ethos/adapters/repo/commit/admission.py"


def test_commit_policy_execution_has_one_semantic_owner() -> None:
    """Policy admission is singular; range selection and history traversal differ."""
    subject_owners, gap_owners, range_owners = set(), set(), set()
    for path in (ROOT / "src/ethos").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == "accepts_subject":
                    subject_owners.add(path)
                arguments = {
                    arg.value
                    for arg in node.args
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                }
                if {"rev-list", "--reverse", "--not"} <= arguments:
                    range_owners.add(path)
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value.startswith(
                    (
                        "commit_subject_invalid:",
                        "commit_signature_missing:",
                        "commit_signature_format_mismatch:",
                    )
                )
            ):
                gap_owners.add(path)
    assert subject_owners == gap_owners == {COMMIT_ADMISSION_OWNER}
    assert range_owners == {ROOT / "src/ethos/adapters/repo/commit/integration.py"}


def test_current_product_boundary_reports_close_without_unowned_references() -> None:
    reports = (product_boundary_report(ROOT),)

    assert all(report["verdict"] == "pass" for report in reports), reports
    closure = repository_semantic_closure(ROOT, retained_origins=observed_document_origins(ROOT))
    assert closure["verdict"] == "pass", closure["required_gaps"]


@pytest.mark.parametrize(
    ("command", "verdict"),
    [
        (("ethos", "status", "--json"), True),
        (("ethos", "plan", "--json"), True),
        (("ethos", "prove", "--json"), False),
        (("ethos", "land", "--json"), False),
        # The next step may read, but hook admission's readers do not widen with it.
        (("ethos", "lane", "status", "--json"), False),
        (("ethos", "publish", "--ref", "refs/heads/dev", "--probe-remote", "--json"), False),
        (("ethos", "hook", "install", "--json"), False),
    ],
)
def test_command_readonly_classification_is_public_and_fail_closed(
    command: tuple[str, ...], verdict: object
) -> None:
    assert ethos_command_is_readonly(command) is verdict
