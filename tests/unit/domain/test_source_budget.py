from __future__ import annotations

import json
from pathlib import Path

import pytest

import ethos.domain.source_budget.measurement as source_budget
from tests.support.governed_repository import git
from tests.support.subprocesses import completed as cp


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
terminal = {{ python_total = {terminal[0]}, global_total = {terminal[1]} }}
immutable_record_roots = ["evidence/", "openspec/changes/archive/"]
line_width = 100

[source_budget.cross_check]
command = "fake-scc"
args = ["--format", "json2", "--exclude-file=__never__"]
timeout_seconds = 5
tolerance = {{ python_total = {tolerance[0]}, global_total = {tolerance[1]} }}

[source_budget.aggregates]
python_total = ["python_product", "python_other"]
global_total = ["python_product", "python_other", "toml", "json", "yaml", "ini", "shell"]

[[format]]
extensions = [".lock", ".json", ".yaml", ".yml"]
[[format.budget]]
category = "dependency_resolution"
paths = [
  "*.lock", "**/*.lock", "*-lock.json", "**/*-lock.json",
  "*-lock.yaml", "**/*-lock.yaml", "*-lock.yml", "**/*-lock.yml",
  "npm-shrinkwrap.json", "**/npm-shrinkwrap.json",
]
accounting = "generated_evidence"

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
            assert "--exclude-file=__never__" in command
            return cp(stdout=payload(), command="scc")
        return run(command, **kwargs)

    monkeypatch.setattr(
        source_budget.shutil,
        "which",
        lambda command: "/fake-scc" if command == "fake-scc" else which(command),
    )
    monkeypatch.setattr(source_budget.subprocess, "run", dispatch)


def test_product_policy_counts_markdown_in_global_budget() -> None:
    root = Path(__file__).resolve().parents[3]
    report = source_budget.source_budget_report(root)

    assert report["inventory"]["category_counts"]["markdown"] > 0
    assert report["metrics"]["global_total"] >= report["metrics"]["markdown"]


def test_direct_measurement_is_clean_when_bounded_counters_agree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    _fake_scc(monkeypatch, tmp_path)

    report = source_budget.source_budget_report(tmp_path)

    assert (report["verdict"], report["state"], report["required_gaps"]) == (
        "pass",
        "clean",
        [],
    )
    assert "ok" not in report
    assert report["metrics"]["python_total"] == 2
    assert report["inventory"]["file_count"] == 3


def test_measurement_separates_exact_immutable_record_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    evidence = tmp_path / "evidence/chronicle/decision.py"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("FIRST = 1\nSECOND = 2\n", encoding="utf-8")
    archive = tmp_path / "openspec/changes/archive/closed/receipt.json"
    archive.parent.mkdir(parents=True)
    archive.write_text('{"closed": true}\n', encoding="utf-8")
    _fake_scc(monkeypatch, tmp_path)

    report = source_budget.source_budget_report(tmp_path)

    assert report["required_gaps"] == []
    assert report["metrics"]["python_total"] == 2
    assert report["metrics"]["record_total"] == 3
    assert report["cross_check"]["file_count"] == report["inventory"]["file_count"]


def test_report_exposes_implementation_and_record_cross_check_totals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    record = tmp_path / "evidence/chronicle/decision.py"
    record.parent.mkdir(parents=True)
    record.write_text("RECORDED = 1\n", encoding="utf-8")
    _fake_scc(
        monkeypatch,
        tmp_path,
        {
            ".config/checks/format/selection.toml": 15,
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


def test_generated_lock_is_dependency_evidence_not_owned_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    _fake_scc(monkeypatch, tmp_path)
    before = source_budget.source_budget_report(tmp_path)
    package_lock = tmp_path / "package-lock.json"
    package_lock.write_text('{\n  "lockfileVersion": 3\n}\n', encoding="utf-8")
    git(tmp_path, "add", package_lock.as_posix())

    report = source_budget.source_budget_report(tmp_path)

    assert report["required_gaps"] == []
    assert report["inventory"]["category_counts"]["dependency_resolution"] == 1
    assert report["metrics"]["global_total"] == before["metrics"]["global_total"]
    assert report["cross_check"]["global_total"] == before["cross_check"]["global_total"]
    assert report["metrics"]["generated_evidence_total"] > 0
    assert report["cross_check"]["file_count"] == report["inventory"]["file_count"]


@pytest.mark.parametrize(
    "relative",
    [
        "uv.lock",
        "Cargo.lock",
        "Gemfile.lock",
        "composer.lock",
        "yarn.lock",
        "package-lock.json",
        "nested/pnpm-lock.yaml",
        "nested/npm-shrinkwrap.json",
    ],
)
def test_ecosystem_lockfile_patterns_share_one_evidence_class(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative: str,
) -> None:
    _repo(tmp_path)
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("resolved dependency graph\n", encoding="utf-8")
    git(tmp_path, "add", path.as_posix())
    _fake_scc(monkeypatch, tmp_path)

    report = source_budget.source_budget_report(tmp_path)

    assert report["inventory"]["category_counts"]["dependency_resolution"] == 1


def test_ordinary_structured_files_cannot_impersonate_lockfile_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    path = tmp_path / "system/clock.json"
    path.parent.mkdir()
    path.write_text('{"source": true}\n', encoding="utf-8")
    git(tmp_path, "add", path.as_posix())
    _fake_scc(monkeypatch, tmp_path)

    report = source_budget.source_budget_report(tmp_path)

    assert report["inventory"]["category_counts"].get("dependency_resolution", 0) == 0
    assert report["inventory"]["category_counts"]["json"] == 1


def test_record_growth_is_visible_without_increasing_implementation_totals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    record = tmp_path / "evidence/chronicle/decision.py"
    record.parent.mkdir(parents=True)
    record.write_text("FIRST = 1\n", encoding="utf-8")
    _fake_scc(monkeypatch, tmp_path)
    before = source_budget.source_budget_report(tmp_path)

    record.write_text("FIRST = 1\nSECOND = 2\nTHIRD = 3\n", encoding="utf-8")
    after = source_budget.source_budget_report(tmp_path)

    assert after["metrics"]["record_total"] == before["metrics"]["record_total"] + 2
    assert after["metrics"]["python_total"] == before["metrics"]["python_total"]
    assert after["metrics"]["global_total"] == before["metrics"]["global_total"]


def test_record_root_does_not_hide_an_unclassified_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    executable = tmp_path / "evidence/chronicle/opaque"
    executable.parent.mkdir(parents=True)
    executable.write_text("opaque\n", encoding="utf-8")
    executable.chmod(0o755)
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


def test_scc_cross_check_accepts_a_stricter_physical_markdown_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path, tolerance=(0, 0))
    _fake_scc(
        monkeypatch,
        tmp_path,
        {
            ".config/checks/format/selection.toml": 20,
            ".ethos/rules.toml": 1,
            "src/ethos/demo.py": 2,
        },
    )

    report = source_budget.source_budget_report(tmp_path)

    assert report["cross_check"]["global_total"] > report["metrics"]["global_total"]
    assert not any("global_total_disagrees" in gap for gap in report["required_gaps"])


def test_scc_file_set_and_canonical_overcount_disagreement_block(
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


@pytest.mark.parametrize(
    "mutation",
    [
        lambda text: text.replace("immutable_record_roots =", "invalid_record_roots ="),
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

    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["metrics"] == {}
    assert report["required_gaps"][0].startswith("source_budget_policy_invalid:")
