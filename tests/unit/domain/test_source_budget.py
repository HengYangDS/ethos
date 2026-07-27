from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.domain.source_budget.measurement as source_budget
from tests.support.contract_helpers import git
from tests.support.subprocesses import completed as cp

if TYPE_CHECKING:
    from pathlib import Path


def _selection(
    root: Path,
    *,
    terminal: tuple[int, int] = (1_000, 2_000),
    tolerance: tuple[int, int] = (100, 200),
) -> Path:
    path = root / ".config/checks/format/selection.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""[source_budget]
contract_version = 1
terminal = {{ python_total = {terminal[0]}, global_total = {terminal[1]} }}
line_width = 100

[source_budget.cross_check]
command = "fake-scc"
args = ["--format", "json2"]
timeout_seconds = 5
tolerance = {{ python_total = {tolerance[0]}, global_total = {tolerance[1]} }}

[source_budget.aggregates]
python_total = ["python_product", "python_other"]
global_total = ["python_product", "python_other", "toml", "json", "yaml", "ini", "shell"]

[[format]]
extensions = [".py"]
budget = [
  {{ category = "python_product", paths = ["src/*"], measure = "python_ast" }},
  {{ category = "python_other", measure = "python_ast" }},
]

[[format]]
extensions = [".toml"]
budget = [{{ category = "toml", measure = "structured", baseline_measure = "lines" }}]

[[format]]
extensions = [".json"]
budget = [{{ category = "json", measure = "structured", baseline_measure = "lines" }}]

[[format]]
extensions = [".yaml", ".yml"]
budget = [{{ category = "yaml", measure = "structured", baseline_measure = "lines" }}]

[[format]]
extensions = [".ini", ".cfg"]
budget = [{{ category = "ini", measure = "structured", baseline_measure = "lines" }}]

[[format]]
extensions = [".sh"]
shebangs = ["sh", "bash", "zsh"]
budget = [
  {{ category = "shell", comment_prefixes = ["#"] }},
]
""",
        encoding="utf-8",
    )
    return path


def _repo(
    root: Path,
    *,
    terminal: tuple[int, int] = (1_000, 2_000),
    tolerance: tuple[int, int] = (100, 200),
) -> tuple[Path, Path]:
    selection = _selection(root, terminal=terminal, tolerance=tolerance)
    source = root / "src/ethos/demo.py"
    source.parent.mkdir(parents=True)
    source.write_text('''"""Not executable."""\nFIRST = 1\nSECOND = 2\n''', encoding="utf-8")
    rules = root / ".ethos/rules.toml"
    rules.parent.mkdir(parents=True)
    rules.write_text(
        "[quality.source_budget.terminal]\n"
        f"python_total = {terminal[0]}\n"
        f"global_total = {terminal[1]}\n",
        encoding="utf-8",
    )
    git(root, "init", "-q", "-b", "dev")
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "baseline",
    )
    return selection, source


def _migrate_to_v2(selection: Path) -> None:
    record_roots = 'immutable_record_roots = ["evidence/", "openspec/changes/archive/"]'
    selection.write_text(
        selection.read_text(encoding="utf-8")
        .replace("contract_version = 1", "contract_version = 2")
        .replace(
            "line_width = 100",
            f"{record_roots}\nline_width = 100",
        ),
        encoding="utf-8",
    )


def _fake_scc(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    counts: dict[str, int] | None = None,
    *,
    include_all: bool = True,
) -> None:
    """Expose an external cross-check fixture through the report boundary."""
    expected = counts or {}
    run = source_budget.subprocess.run
    which = source_budget.shutil.which

    def payload() -> str:
        completed = run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
        paths = completed.stdout.splitlines()
        if not include_all:
            paths = [path for path in paths if path in expected]
        return json.dumps(
            {
                "languageSummary": [
                    {
                        "Name": "fixture",
                        "Files": [
                            {
                                "Location": (root / path).as_posix(),
                                "Code": expected.get(path, 0),
                            }
                            for path in paths
                        ],
                    }
                ]
            }
        )

    def dispatch(command, **kwargs):
        if command[0] == "/fake-scc":
            return cp(stdout=payload(), command="scc")
        return run(command, **kwargs)

    monkeypatch.setattr(
        source_budget.shutil,
        "which",
        lambda command: "/fake-scc" if command == "fake-scc" else which(command),
    )
    monkeypatch.setattr(source_budget.subprocess, "run", dispatch)


def test_direct_measurement_is_clean_when_bounded_counters_agree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    _fake_scc(monkeypatch, tmp_path)

    report = source_budget.source_budget_report(tmp_path)

    assert (report["ok"], report["state"], report["required_gaps"]) == (
        True,
        "clean",
        [],
    )
    assert report["metrics"]["python_total"] == 2
    assert report["inventory"]["file_count"] == 3


def test_v2_migration_separates_exact_immutable_record_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection, _source = _repo(tmp_path)
    evidence = tmp_path / "evidence/chronicle/decision.py"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("FIRST = 1\nSECOND = 2\n", encoding="utf-8")
    archive = tmp_path / "openspec/changes/archive/closed/receipt.json"
    archive.parent.mkdir(parents=True)
    archive.write_text('{"closed": true}\n', encoding="utf-8")
    _migrate_to_v2(selection)
    _fake_scc(monkeypatch, tmp_path)

    report = source_budget.source_budget_report(tmp_path)

    assert report["required_gaps"] == []
    assert report["metrics"]["python_total"] == 2
    assert report["metrics"]["record_total"] == 3
    assert report["cross_check"]["file_count"] == report["inventory"]["file_count"]


def test_v2_report_exposes_implementation_and_record_cross_check_totals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection, _source = _repo(tmp_path)
    record = tmp_path / "evidence/chronicle/decision.py"
    record.parent.mkdir(parents=True)
    record.write_text("RECORDED = 1\n", encoding="utf-8")
    _migrate_to_v2(selection)
    _fake_scc(
        monkeypatch,
        tmp_path,
        {
            ".config/checks/format/selection.toml": 12,
            ".ethos/rules.toml": 1,
            "src/ethos/demo.py": 2,
            "evidence/chronicle/decision.py": 1,
        },
    )

    report = source_budget.source_budget_report(tmp_path)

    assert report["required_gaps"] == []
    assert report["cross_check"]["python_total"] == report["metrics"]["python_total"]
    assert report["cross_check"]["global_total"] == report["metrics"]["global_total"]
    assert report["metrics"]["record_total"] == 1
    assert report["cross_check"]["record_total"] == 1
    assert report["cross_check"]["file_count"] == report["inventory"]["file_count"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda text: text.replace(
            "line_width = 100",
            'exclude = ["src/ethos/demo.py"]\nline_width = 100',
        ),
        lambda text: text.replace(
            'paths = ["src/*"]',
            'paths = ["src/other/*"]',
        ),
    ],
)
def test_v2_migration_rejects_arbitrary_excludes_and_path_moves(
    tmp_path: Path,
    mutation,
) -> None:
    selection, _source = _repo(tmp_path)
    _migrate_to_v2(selection)
    selection.write_text(mutation(selection.read_text(encoding="utf-8")), encoding="utf-8")

    report = source_budget.source_budget_report(tmp_path)

    assert report["required_gaps"] == ["source_budget_policy_relaxed"]


def test_v2_record_growth_is_visible_without_increasing_implementation_totals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection, _source = _repo(tmp_path)
    record = tmp_path / "evidence/chronicle/decision.py"
    record.parent.mkdir(parents=True)
    record.write_text("FIRST = 1\n", encoding="utf-8")
    _migrate_to_v2(selection)
    _fake_scc(monkeypatch, tmp_path)
    before = source_budget.source_budget_report(tmp_path)

    record.write_text("FIRST = 1\nSECOND = 2\nTHIRD = 3\n", encoding="utf-8")
    after = source_budget.source_budget_report(tmp_path)

    assert after["metrics"]["record_total"] == before["metrics"]["record_total"] + 2
    assert after["metrics"]["python_total"] == before["metrics"]["python_total"]
    assert after["metrics"]["global_total"] == before["metrics"]["global_total"]


def test_v2_record_root_does_not_hide_an_unclassified_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection, _source = _repo(tmp_path)
    executable = tmp_path / "evidence/chronicle/opaque"
    executable.parent.mkdir(parents=True)
    executable.write_text("opaque\n", encoding="utf-8")
    executable.chmod(0o755)
    _migrate_to_v2(selection)
    _fake_scc(monkeypatch, tmp_path)

    report = source_budget.source_budget_report(tmp_path)

    expected = "source_budget_executable_unclassified:evidence/chronicle/opaque"
    assert expected in report["required_gaps"]


def test_terminal_verdict_uses_the_conservative_counter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path, terminal=(2, 2_000))
    _fake_scc(monkeypatch, tmp_path, {"src/ethos/demo.py": 3})

    report = source_budget.source_budget_report(tmp_path)

    assert "source_budget_terminal_exceeded:python_total:3>2" in report["required_gaps"]
    assert report["enforced_metrics"]["python_total"] == 3


def test_extensionless_hook_is_counted_and_unknown_executable_blocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    hook = tmp_path / ".githooks/pre-push"
    hook.parent.mkdir()
    hook.write_text("#!/bin/sh\necho ready\n", encoding="utf-8")
    hook.chmod(0o755)
    unknown = tmp_path / "bin/tool"
    unknown.parent.mkdir()
    unknown.write_text("opaque\n", encoding="utf-8")
    unknown.chmod(0o755)
    git(tmp_path, "add", ".")
    _fake_scc(monkeypatch, tmp_path)

    report = source_budget.source_budget_report(tmp_path)

    assert report["metrics"]["shell"] >= 1
    assert "source_budget_executable_unclassified:bin/tool" in report["required_gaps"]


def test_scc_file_set_and_bidirectional_total_disagreement_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path, tolerance=(0, 0))
    _fake_scc(
        monkeypatch,
        tmp_path,
        {"src/ethos/demo.py": 4},
        include_all=False,
    )

    report = source_budget.source_budget_report(tmp_path)

    assert any(gap.startswith("source_budget_scc_file_missing:") for gap in report["required_gaps"])
    assert any("_disagrees:" in gap for gap in report["required_gaps"])


def test_structured_measurement_cannot_be_reduced_by_minifying_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    data = tmp_path / "system/data.json"
    data.parent.mkdir()
    value = {"items": [{"name": f"item-{index}", "enabled": True} for index in range(20)]}
    data.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    _fake_scc(monkeypatch, tmp_path)
    pretty = source_budget.source_budget_report(tmp_path)["metrics"]["json"]

    data.write_text(json.dumps(value, separators=(",", ":")) + "\n", encoding="utf-8")
    compact = source_budget.source_budget_report(tmp_path)["metrics"]["json"]

    assert compact == pretty


@pytest.mark.parametrize(
    ("category", "suffix", "first", "second"),
    [
        ("json", ".json", '{"a": 1, "b": [2, 3]}\n', '{\n  "b": [2, 3],\n  "a": 1\n}\n'),
        ("toml", ".toml", "a = 1\nb = [2, 3]\n", "b=[2,3]\na=1\n"),
        ("yaml", ".yaml", "a: 1\nb: [2, 3]\n", "b:\n  - 2\n  - 3\na: 1\n"),
        ("ini", ".ini", "[section]\na = 1\nb = 2\n", "[section]\nb=2\na=1\n"),
    ],
)
def test_structured_measurement_is_formatting_and_order_invariant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    category: str,
    suffix: str,
    first: str,
    second: str,
) -> None:
    _repo(tmp_path)
    path = tmp_path / f"system/data{suffix}"
    path.parent.mkdir()
    path.write_text(first, encoding="utf-8")
    git(tmp_path, "add", ".")
    _fake_scc(monkeypatch, tmp_path)
    before = source_budget.source_budget_report(tmp_path)["metrics"][category]

    path.write_text(second, encoding="utf-8")
    after = source_budget.source_budget_report(tmp_path)["metrics"][category]

    assert after == before


def test_yaml_measurement_accepts_native_mixed_scalar_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    path = tmp_path / "system/data.yaml"
    path.parent.mkdir()
    path.write_text("on: enabled\ntrue: boolean-key\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    _fake_scc(monkeypatch, tmp_path)

    report = source_budget.source_budget_report(tmp_path)

    assert report["metrics"]["yaml"] > 0


def test_policy_rejects_relaxation_in_accepted_baseline(tmp_path: Path) -> None:
    selection, _ = _repo(tmp_path, terminal=(100, 200), tolerance=(1, 2))
    selection.write_text(
        selection.read_text()
        .replace("python_total = 100, global_total = 200", "python_total = 101, global_total = 200")
        .replace("python_total = 1, global_total = 2", "python_total = 2, global_total = 2"),
        encoding="utf-8",
    )

    report = source_budget.source_budget_report(tmp_path)

    assert report["required_gaps"] == ["source_budget_policy_relaxed"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda text: text.replace('command = "fake-scc"', 'command = "other-scc"'),
        lambda text: text.replace(
            'args = ["--format", "json2"]',
            'args = ["--format", "json"]',
        ),
        lambda text: text.replace(
            'paths = ["src/*"]',
            'paths = ["src/other/*"]',
        ),
        lambda text: text.replace('extensions = [".py"]', 'extensions = [".pyi"]'),
        lambda text: text.replace(
            'shebangs = ["sh", "bash", "zsh"]',
            'shebangs = ["sh"]',
        ),
        lambda text: text.replace(
            ('{ category = "python_product", paths = ["src/*"], measure = "python_ast" }'),
            ('{ category = "python_product", paths = ["src/*"], measure = "lines" }'),
        ).replace(
            'python_total = ["python_product", "python_other"]',
            'python_total = ["python_other"]',
        ),
        lambda text: text.replace(
            '{ category = "shell", comment_prefixes = ["#"] }',
            '{ category = "shell", comment_prefixes = ["#", "echo"] }',
        ),
        lambda text: text.replace(
            ', "json", "yaml", "ini", "shell"]',
            ', "yaml", "ini", "shell"]',
        ).replace(
            """[[format]]
extensions = [".json"]
budget = [{ category = "json", measure = "structured", baseline_measure = "lines" }]

""",
            "",
        ),
    ],
)
def test_policy_rejects_measurement_contract_rewrites(
    tmp_path: Path,
    mutation,
) -> None:
    selection, _ = _repo(tmp_path)
    selection.write_text(mutation(selection.read_text()), encoding="utf-8")

    report = source_budget.source_budget_report(tmp_path)

    assert report["required_gaps"] == ["source_budget_policy_relaxed"]


def test_first_versioned_policy_uses_candidate_control_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection, _ = _repo(tmp_path)
    current = selection.read_text(encoding="utf-8")
    accepted = (
        "\n".join(
            line
            for line in current.splitlines()
            if not line.startswith(
                ("contract_version =", "cross_check =", "terminal =", "line_width =")
            )
        )
        + "\n"
    )
    selection.write_text(accepted, encoding="utf-8")
    git(tmp_path, "add", ".")
    git(
        tmp_path,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "invalid accepted policy",
    )
    selection.write_text(current, encoding="utf-8")
    _fake_scc(monkeypatch, tmp_path)

    report = source_budget.source_budget_report(tmp_path)

    assert report["ok"] is True
    assert report["terminal"] == {"python_total": 1_000, "global_total": 2_000}


def test_accepted_ref_and_files_fail_closed(tmp_path: Path) -> None:
    selection, _ = _repo(tmp_path)
    current = selection.read_text(encoding="utf-8")
    git(tmp_path, "branch", "-m", "other")
    report = source_budget.source_budget_report(tmp_path)
    assert report["required_gaps"] == ["source_budget_accepted_ref_unavailable"]

    git(tmp_path, "branch", "-m", "dev")
    git(tmp_path, "rm", selection.as_posix())
    git(
        tmp_path,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "remove accepted policy",
    )
    selection.parent.mkdir(parents=True, exist_ok=True)
    selection.write_text(current, encoding="utf-8")

    report = source_budget.source_budget_report(tmp_path)

    assert report["required_gaps"] == [
        "source_budget_accepted_file_unavailable:.config/checks/format/selection.toml",
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda text: text.replace("contract_version = 1\n", ""),
        lambda text: text.replace(', "shell"]', "]"),
        lambda text: text.replace('shebangs = ["sh", "bash", "zsh"]', 'shebangs = "sh"'),
        lambda text: text.replace('comment_prefixes = ["#"]', 'comment_prefixes = "#"', 1),
    ],
)
def test_malformed_or_incomplete_policy_fails_closed(
    tmp_path: Path,
    mutation,
) -> None:
    selection, _ = _repo(tmp_path)
    selection.write_text(mutation(selection.read_text()), encoding="utf-8")

    report = source_budget.source_budget_report(tmp_path)

    assert report["ok"] is False
    assert report["metrics"] == {}
    assert report["required_gaps"][0].startswith("source_budget_policy_invalid:")
