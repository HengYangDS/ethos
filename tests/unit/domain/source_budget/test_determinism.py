"""Public budget observations preserve deterministic failure and measurement semantics."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import tomli_w

import ethos.domain.source_budget.measurement as measurement
from tests.support.governed_repository import git
from tests.support.source_budget import fake_scc
from tests.support.source_budget import write_budget_selection

ROOT = Path(__file__).resolve().parents[4]


def _repository(tmp_path: Path) -> Path:
    selection = write_budget_selection(
        tmp_path,
        terminal=(100, 100, 100, 100, 200),
        tolerance=(100, 100),
    )
    policy = tomllib.loads(selection.read_text())
    python = next(item for item in policy["format"] if item["extensions"] == [".py"])
    python["shebangs"] = ["python"]
    policy["format"] = [
        python,
        {
            "extensions": [".unknown"],
            "budget": [{"category": "structured", "measure": "structured"}],
        },
    ]
    policy["source_budget"]["aggregates"]["global_total"] = [
        *(item["category"] for item in python["budget"]),
        "structured",
    ]
    selection.write_text(tomli_w.dumps(policy))
    git(tmp_path, "init", "-q", "-b", "dev")
    return tmp_path


@pytest.mark.parametrize("field", ["terminal", "cross_check"])
def test_source_budget_public_report_rejects_wrong_policy_container(tmp_path, field):
    root = _repository(tmp_path)
    path = root / ".config/checks/format/selection.toml"
    policy = tomllib.loads(path.read_text())
    if field == "terminal":
        policy["source_budget"][field] = []
    else:
        policy["source_budget"][field]["args"] = {}
    path.write_text(tomli_w.dumps(policy))
    report = measurement.source_budget_report(root)
    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["source_budget_policy_invalid:shape"]


def test_source_budget_public_report_normalizes_env_interpreters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repository(tmp_path)
    for name, shebang in (
        ("isolated", "#!/usr/bin/env -S python -I\n"),
        ("plain", "#!/usr/bin/env python\n"),
    ):
        path = root / name
        path.write_text(f"{shebang}VALUE = 1\n", encoding="utf-8")
        path.chmod(0o755)
    git(root, "add", ".")
    fake_scc(monkeypatch, root)

    report = measurement.source_budget_report(root)

    assert report["inventory"]["category_counts"]["python_other"] == 2
    assert report["metrics"]["python_other"] == 2


def test_source_budget_public_report_rejects_unsupported_structured_suffix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repository(tmp_path)
    (root / "value.unknown").write_text("value", encoding="utf-8")
    git(root, "add", ".")
    fake_scc(monkeypatch, root)

    report = measurement.source_budget_report(root)

    assert "source_budget_carrier_unreadable:value.unknown" in report["required_gaps"]
    assert report["inventory"]["file_count"] == 0


@pytest.mark.parametrize(
    ("location", "code", "immutable", "gap"),
    [
        (None, 1, False, "source_budget_scc_file_missing:src/example.py"),
        ("", 1, False, "source_budget_scc_file_missing:src/example.py"),
        ("/outside/root.py", 1, False, "source_budget_scc_file_missing:src/example.py"),
        ("source", True, False, "source_budget_scc_invalid"),
        ("source", "1", False, "source_budget_scc_invalid"),
        ("source", True, True, "source_budget_scc_invalid"),
    ],
)
def test_cross_check_rejects_invalid_locations_and_source_or_immutable_counts(
    tmp_path,
    monkeypatch,
    location,
    code,
    immutable,
    gap,
):
    """Location and count failures remain distinct in source and archive planes."""
    root = _repository(tmp_path)
    source = root / "src/example.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n")
    counts = {source.as_posix() if location == "source" else location: code}
    if immutable:
        record = root / "openspec/changes/archive/record.py"
        record.parent.mkdir(parents=True)
        record.write_text("VALUE = 1\n")
        counts = {source.as_posix(): 1, record.as_posix(): code}
    git(root, "add", ".")
    fake_scc(monkeypatch, root, counts, include_all=False)
    report = measurement.source_budget_report(root)
    assert report["verdict"] == "block"
    assert gap in report["required_gaps"]
