from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import ethos.domain.source_budget.measurement as measurement
from tests.support.governed_repository import git
from tests.support.subprocesses import completed

if TYPE_CHECKING:
    from collections.abc import Callable


ROOT = Path(__file__).resolve().parents[3]


def _repository(tmp_path: Path, *, extra_format: str = "") -> Path:
    selection = tmp_path / ".config/checks/format/selection.toml"
    selection.parent.mkdir(parents=True)
    selection.write_text(
        """[source_budget]
immutable_record_roots = ["evidence/", "openspec/changes/archive/"]
line_width = 100

[source_budget.terminal]
python_product = 100
python_tests = 100
python_tools = 100
python_other = 100
global_total = 200

[source_budget.cross_check]
command = "fake-scc"
args = ["--format", "json2"]
timeout_seconds = 5
tolerance = { python_total = 100, global_total = 100 }

[source_budget.aggregates]
python_total = ["python_product", "python_tests", "python_tools", "python_other"]
global_total = ["python_product", "python_tests", "python_tools", "python_other", "structured"]

[[format]]
extensions = [".py"]
shebangs = ["python"]
budget = [
  { category = "python_product", paths = ["src/*"], measure = "python_ast" },
  { category = "python_tests", paths = ["tests/*"], measure = "python_ast" },
  { category = "python_tools", paths = ["tools/*"], measure = "python_ast" },
  { category = "python_other", measure = "python_ast" },
]

[[format]]
extensions = [".unknown"]
budget = [{ category = "structured", measure = "structured" }]
"""
        + extra_format,
        encoding="utf-8",
    )
    git(tmp_path, "init", "-q", "-b", "dev")
    return tmp_path


def _fake_scc(
    monkeypatch: pytest.MonkeyPatch,
    payload: Callable[[Path], object],
) -> None:
    which = measurement.shutil.which
    run_command = measurement.subprocess.run
    monkeypatch.setattr(
        measurement.shutil,
        "which",
        lambda command, **kwargs: (
            "/fake-scc" if command == "fake-scc" else which(command, **kwargs)
        ),
    )

    def run(command, **kwargs):
        return (
            completed(stdout=json.dumps(payload(Path(kwargs["cwd"]))))
            if command[0] == "/fake-scc"
            else run_command(command, **kwargs)
        )

    monkeypatch.setattr(measurement.subprocess, "run", run)


def _scc_files(root: Path) -> object:
    return {
        "languageSummary": [
            {
                "Name": "fixture",
                "Files": [
                    {"Location": path.as_posix(), "Code": 0}
                    for path in root.rglob("*")
                    if path.is_file()
                ],
            }
        ]
    }


@pytest.mark.parametrize(
    "body",
    [
        "[source_budget]\nterminal = []\n",
        """[source_budget]
immutable_record_roots = ["evidence/", "openspec/changes/archive/"]
line_width = 100

[source_budget.terminal]
python_product = 1
python_tests = 1
python_tools = 1
python_other = 1
global_total = 2
[source_budget.cross_check]
command = "scc"
args = {}
timeout_seconds = 1
tolerance = { python_total = 0, global_total = 0 }
""",
    ],
)
def test_source_budget_public_report_rejects_wrong_policy_container(
    tmp_path: Path, body: str
) -> None:
    path = tmp_path / ".config/checks/format/selection.toml"
    path.parent.mkdir(parents=True)
    path.write_text(body, encoding="utf-8")

    report = measurement.source_budget_report(tmp_path)

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
    _fake_scc(monkeypatch, _scc_files)

    report = measurement.source_budget_report(root)

    assert report["inventory"]["category_counts"]["python_other"] == 2
    assert report["metrics"]["python_other"] == 2


def test_source_budget_public_report_rejects_unsupported_structured_suffix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repository(tmp_path)
    (root / "value.unknown").write_text("value", encoding="utf-8")
    git(root, "add", ".")
    _fake_scc(monkeypatch, _scc_files)

    report = measurement.source_budget_report(root)

    assert "source_budget_carrier_unreadable:value.unknown" in report["required_gaps"]
    assert report["inventory"]["file_count"] == 0


@pytest.mark.parametrize("location", [None, "", "/outside/root.py"])
def test_source_budget_public_cross_check_rejects_invalid_or_external_locations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    location: object,
) -> None:
    root = _repository(tmp_path)
    source = root / "src/example.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")
    git(root, "add", ".")
    _fake_scc(
        monkeypatch,
        lambda _root: {
            "languageSummary": [{"Name": "fixture", "Files": [{"Location": location, "Code": 1}]}]
        },
    )

    report = measurement.source_budget_report(root)

    assert report["verdict"] == "block"
    assert "source_budget_scc_file_missing:src/example.py" in report["required_gaps"]


@pytest.mark.parametrize("code", [True, "1"])
def test_source_budget_public_cross_check_rejects_invalid_counts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    code: object,
) -> None:
    root = _repository(tmp_path)
    source = root / "src/example.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")
    git(root, "add", ".")
    _fake_scc(
        monkeypatch,
        lambda _root: {
            "languageSummary": [
                {"Name": "fixture", "Files": [{"Location": source.as_posix(), "Code": code}]}
            ]
        },
    )

    report = measurement.source_budget_report(root)

    assert report["verdict"] == "block"
    assert "source_budget_scc_invalid" in report["required_gaps"]


def test_source_budget_public_cross_check_rejects_invalid_immutable_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repository(tmp_path)
    source = root / "src/example.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")
    record = root / "evidence/record.py"
    record.parent.mkdir()
    record.write_text("VALUE = 1\n", encoding="utf-8")
    git(root, "add", ".")
    _fake_scc(
        monkeypatch,
        lambda _root: {
            "languageSummary": [
                {
                    "Name": "fixture",
                    "Files": [
                        {"Location": source.as_posix(), "Code": 1},
                        {"Location": record.as_posix(), "Code": True},
                    ],
                }
            ]
        },
    )

    report = measurement.source_budget_report(root)

    assert report["verdict"] == "block"
    assert "source_budget_scc_invalid" in report["required_gaps"]
