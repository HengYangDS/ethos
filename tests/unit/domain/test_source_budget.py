from __future__ import annotations

import json
from pathlib import Path

import pytest

import ethos.domain.source_budget.measurement as source_budget
from ethos.domain.source_budget.measurement_policy import PYTHON_CATEGORIES
from tests.support.governed_repository import git
from tests.support.subprocesses import completed as cp


def _selection(
    root: Path,
    *,
    terminal: tuple[int, int, int, int, int] = (1_000, 1_000, 1_000, 1_000, 2_000),
    tolerance: tuple[int, int] = (100, 200),
) -> Path:
    path = root / ".config/checks/format/selection.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "[source_budget]\n"
        "terminal = { "
        f"python_product = {terminal[0]}, python_tests = {terminal[1]}, "
        f"python_tools = {terminal[2]}, python_other = {terminal[3]}, "
        f"global_total = {terminal[4]} }}\n"
        f"""immutable_record_roots = ["evidence/", "openspec/changes/archive/"]
line_width = 100

[source_budget.cross_check]
command = "fake-scc"
args = ["--format", "json2", "--exclude-file=__never__"]
timeout_seconds = 5
tolerance = {{ python_total = {tolerance[0]}, global_total = {tolerance[1]} }}

[source_budget.aggregates]
python_total = ["python_product", "python_tests", "python_tools", "python_other"]
global_total = [
  "python_product", "python_tests", "python_tools", "python_other",
  "toml", "json", "yaml", "ini", "shell",
]

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
  {{ category = "python_tests", paths = ["tests/*"], measure = "python_ast" }},
  {{ category = "python_tools", paths = ["tools/*"], measure = "python_ast" }},
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
    terminal: tuple[int, int, int, int, int] = (1_000, 1_000, 1_000, 1_000, 2_000),
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
        f"python_product = {terminal[0]}\n"
        f"python_tests = {terminal[1]}\n"
        f"python_tools = {terminal[2]}\n"
        f"python_other = {terminal[3]}\n"
        f"global_total = {terminal[4]}\n",
        encoding="utf-8",
    )
    git(root, "init", "-q", "-b", "dev")
    git(root, "add", ".")
    git(
        root,
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
        lambda command, **kwargs: (
            "/fake-scc" if command == "fake-scc" else which(command, **kwargs)
        ),
    )
    monkeypatch.setattr(source_budget.subprocess, "run", dispatch)


def _measure(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    counts: dict[str, int] | None = None,
    *,
    include_all: bool = True,
) -> dict[str, object]:
    _fake_scc(monkeypatch, root, counts, include_all=include_all)
    return source_budget.source_budget_report(root)


def _tracked_file(
    root: Path,
    relative: str,
    content: str,
    *,
    executable: bool = False,
) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if executable:
        path.chmod(0o755)
    git(root, "add", path.as_posix())
    return path


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
    report = _measure(monkeypatch, tmp_path)

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
    _tracked_file(tmp_path, "evidence/chronicle/decision.py", "FIRST = 1\nSECOND = 2\n")
    _tracked_file(tmp_path, "openspec/changes/archive/closed/receipt.json", '{"closed": true}\n')
    report = _measure(monkeypatch, tmp_path)

    assert report["required_gaps"] == []
    assert report["metrics"]["python_total"] == 2
    assert report["metrics"]["record_total"] == 3
    assert report["cross_check"]["file_count"] == report["inventory"]["file_count"]


def test_report_exposes_implementation_and_record_cross_check_totals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    _tracked_file(tmp_path, "evidence/chronicle/decision.py", "RECORDED = 1\n")
    report = _measure(
        monkeypatch,
        tmp_path,
        {
            ".config/checks/format/selection.toml": 15,
            ".ethos/rules.toml": 1,
            "src/ethos/demo.py": 2,
            "evidence/chronicle/decision.py": 1,
        },
    )

    assert report["required_gaps"] == []
    assert report["cross_check"]["python_total"] == report["metrics"]["python_total"]
    assert report["cross_check"]["global_total"] <= report["metrics"]["global_total"]
    assert report["metrics"]["record_total"] == 1
    assert report["cross_check"]["record_total"] == 1
    assert report["cross_check"]["file_count"] == report["inventory"]["file_count"]


def test_generated_lock_is_dependency_evidence_not_owned_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    before = _measure(monkeypatch, tmp_path)
    _tracked_file(tmp_path, "package-lock.json", '{\n  "lockfileVersion": 3\n}\n')
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
    _tracked_file(tmp_path, relative, "resolved dependency graph\n")
    report = _measure(monkeypatch, tmp_path)

    assert report["inventory"]["category_counts"]["dependency_resolution"] == 1


def test_ordinary_structured_files_cannot_impersonate_lockfile_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    _tracked_file(tmp_path, "system/clock.json", '{"source": true}\n')
    report = _measure(monkeypatch, tmp_path)

    assert report["inventory"]["category_counts"].get("dependency_resolution", 0) == 0
    assert report["inventory"]["category_counts"]["json"] == 1


def test_record_growth_is_visible_without_increasing_implementation_totals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    record = _tracked_file(tmp_path, "evidence/chronicle/decision.py", "FIRST = 1\n")
    before = _measure(monkeypatch, tmp_path)

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
    _tracked_file(tmp_path, "evidence/chronicle/opaque", "opaque\n", executable=True)
    report = _measure(monkeypatch, tmp_path)

    expected = "source_budget_executable_unclassified:evidence/chronicle/opaque"
    assert expected in report["required_gaps"]


def test_terminal_verdict_uses_canonical_effective_lines_not_physical_cross_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path, terminal=(2, 1_000, 1_000, 1_000, 2_000))
    report = _measure(monkeypatch, tmp_path, {"src/ethos/demo.py": 3})

    assert report["metrics"]["python_total"] == 2
    assert report["cross_check"]["python_total"] == 3
    assert report["enforced_metrics"]["python_product"] == 2
    assert not any("terminal_exceeded:python_product" in gap for gap in report["required_gaps"])


@pytest.mark.parametrize(
    ("category", "relative", "terminal"),
    [
        ("python_product", None, (1, 1_000, 1_000, 1_000, 2_000)),
        ("python_tests", "tests/test_demo.py", (1_000, 1, 1_000, 1_000, 2_000)),
        ("python_tools", "tools/demo.py", (1_000, 1_000, 1, 1_000, 2_000)),
        ("python_other", "demo.py", (1_000, 1_000, 1_000, 1, 2_000)),
    ],
)
def test_python_carrier_roles_cannot_compensate_for_one_another(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    category: str,
    relative: str | None,
    terminal: tuple[int, int, int, int, int],
) -> None:
    _repo(tmp_path, terminal=terminal)
    if relative is not None:
        _tracked_file(tmp_path, relative, "FIRST = 1\nSECOND = 2\n")
    report = _measure(monkeypatch, tmp_path)

    assert report["enforced_metrics"][category] == 2
    assert f"source_budget_terminal_exceeded:{category}:2>1" in report["required_gaps"]
    assert not any("terminal_exceeded:global_total" in gap for gap in report["required_gaps"])


def test_python_role_partition_is_complete_and_non_overlapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    for relative in ("tests/test_demo.py", "tools/demo.py", "demo.py"):
        _tracked_file(tmp_path, relative, "FIRST = 1\nSECOND = 2\n")
    report = _measure(monkeypatch, tmp_path)

    assert {role: report["metrics"][role] for role in PYTHON_CATEGORIES} == {
        "python_product": 2,
        "python_tests": 2,
        "python_tools": 2,
        "python_other": 2,
    }
    assert report["metrics"]["python_total"] == 8


def test_overlapping_python_role_patterns_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection, _ = _repo(tmp_path)
    selection.write_text(
        selection.read_text().replace(
            'category = "python_product", paths = ["src/*"]',
            'category = "python_product", paths = ["src/*", "tests/*"]',
        ),
        encoding="utf-8",
    )
    _tracked_file(tmp_path, "tests/test_demo.py", "FIRST = 1\nSECOND = 2\n")
    report = _measure(monkeypatch, tmp_path)

    assert report["verdict"] == "block"
    assert (
        "source_budget_python_role_ambiguous:tests/test_demo.py:python_product,python_tests"
        in report["required_gaps"]
    )


def test_global_total_blocks_without_any_python_role_exceeding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path, terminal=(1_000, 1_000, 1_000, 1_000, 1))
    report = _measure(monkeypatch, tmp_path)

    assert "source_budget_terminal_exceeded:global_total:" in "\n".join(report["required_gaps"])
    assert not any(
        f"terminal_exceeded:{category}" in gap
        for category in PYTHON_CATEGORIES
        for gap in report["required_gaps"]
    )


def test_extensionless_hook_is_counted_and_unknown_executable_blocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    _tracked_file(tmp_path, ".githooks/pre-push", "#!/bin/sh\necho ready\n", executable=True)
    _tracked_file(tmp_path, "bin/tool", "opaque\n", executable=True)
    report = _measure(monkeypatch, tmp_path)

    assert report["metrics"]["shell"] >= 1
    assert "source_budget_executable_unclassified:bin/tool" in report["required_gaps"]


def test_scc_cross_check_accepts_a_stricter_physical_markdown_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path, tolerance=(0, 0))
    report = _measure(
        monkeypatch,
        tmp_path,
        {
            ".config/checks/format/selection.toml": 20,
            ".ethos/rules.toml": 1,
            "src/ethos/demo.py": 2,
        },
    )

    assert report["cross_check"]["global_total"] > report["metrics"]["global_total"]
    assert not any("global_total_disagrees" in gap for gap in report["required_gaps"])


def test_scc_file_set_and_canonical_overcount_disagreement_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path, tolerance=(0, 0))
    report = _measure(
        monkeypatch,
        tmp_path,
        {"src/ethos/demo.py": 4},
        include_all=False,
    )

    assert any(gap.startswith("source_budget_scc_file_missing:") for gap in report["required_gaps"])
    assert any("_disagrees:" in gap for gap in report["required_gaps"])


def test_structured_measurement_cannot_be_reduced_by_minifying_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    value = {"items": [{"name": f"item-{index}", "enabled": True} for index in range(20)]}
    data = _tracked_file(tmp_path, "system/data.json", json.dumps(value, indent=2) + "\n")
    pretty = _measure(monkeypatch, tmp_path)["metrics"]["json"]

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
    path = _tracked_file(tmp_path, f"system/data{suffix}", first)
    before = _measure(monkeypatch, tmp_path)["metrics"][category]

    path.write_text(second, encoding="utf-8")
    after = source_budget.source_budget_report(tmp_path)["metrics"][category]

    assert after == before


def test_yaml_measurement_accepts_native_mixed_scalar_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repo(tmp_path)
    _tracked_file(tmp_path, "system/data.yaml", "on: enabled\ntrue: boolean-key\n")
    report = _measure(monkeypatch, tmp_path)

    assert report["metrics"]["yaml"] > 0


@pytest.mark.parametrize(
    "mutation",
    [
        lambda text: text.replace("immutable_record_roots =", "invalid_record_roots ="),
        lambda text: text.replace('  "toml", "json", "yaml", "ini", "shell",\n', ""),
        lambda text: text.replace(
            'python_total = ["python_product", "python_tests", "python_tools", "python_other"]',
            'python_total = ["python_tests", "python_product", "python_tools", "python_other"]',
        ),
        lambda text: text.replace("python_other = 1000", "python_unknown = 1000"),
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
