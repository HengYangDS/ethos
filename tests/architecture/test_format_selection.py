"""Tracked-carrier ownership closure."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import tools.ci.format_selection as format_selection
from ethos.adapters.gates.formatting import render_source_content
from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module
from ethos.repository.policy.quality.format_selection import audit
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

ROOT = Path(__file__).resolve().parents[2]


def test_packaged_agent_guidance_is_selected_by_native_markdown_lint() -> None:
    """A new shipped Markdown resource cannot sit outside the executed lint scope."""
    config = yaml.safe_load(
        (ROOT / ".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml").read_text(
            encoding="utf-8"
        )
    )
    path = ROOT / "src/ethos/resources/skills/ethos-repository-work/SKILL.md"
    assert any(path in ROOT.glob(pattern) for pattern in config["globs"])


@pytest.fixture(scope="module")
def carrier_report():
    return json.loads(
        subprocess.check_output(
            (sys.executable, "tools/ci/format_selection.py"),
            cwd=ROOT,
            text=True,
        )
    )


def test_format_selection_receipt_exposes_owner_for_every_tracked_file(carrier_report) -> None:
    payload = carrier_report
    assert payload["verdict"] == "pass"
    assert payload["tracked_file_count"] == len(payload["assignments"])
    assert not any(
        payload[key]
        for key in ("unowned_file_count", "multiply_owned_file_count", "unverified_file_count")
    )
    fields = (
        "format_owner",
        "format_check",
        "validation_owner",
        "validation_command",
        "mutation_policy",
    )
    assert all(entry[field] for entry in payload["assignments"] for field in fields)


def test_current_openspec_markdown_has_generic_and_semantic_validation(carrier_report) -> None:
    assignments = {entry["path"]: entry for entry in carrier_report["assignments"]}
    selected = {"openspec/config.yaml", "openspec/specs/quality/spec.md"}
    selected.update(path for path in assignments if Path(path).match("openspec/changes/*/tasks.md"))
    for relative in sorted(selected):
        assignment = assignments[relative]
        assert assignment["format_owner"] == "prettier"
        assert assignment["format_check"] == "ethos lane format --check"
        assert assignment["mutation_policy"] == "native-formatter"
        assert assignment["validation_owner"] == "official-openspec"
        assert assignment["validation_command"] == "ethos prove --gate openspec --json"
        assert assignment["semantic_companions"]


def test_immutable_markdown_is_linted_without_rewrite_authority(carrier_report) -> None:
    assignments = carrier_report["assignments"]
    immutable = [
        entry
        for entry in assignments
        if entry["path"].startswith("openspec/changes/archive/") and entry["path"].endswith(".md")
    ]

    assert immutable
    assert {entry["mutation_policy"] for entry in immutable} == {"forbidden"}
    assert {entry["format_owner"] for entry in immutable} == {"immutable-carrier"}
    assert {entry["validation_owner"] for entry in immutable} == {"markdownlint-cli2"}


def test_native_carriers_separate_canonicalization_from_validation(
    carrier_report, tmp_path
) -> None:
    assignments = {entry["path"]: entry for entry in carrier_report["assignments"]}

    expected = {
        "src/ethos/cli.py": ("ruff", "ruff"),
        "pyproject.toml": ("taplo", "taplo"),
        ".github/workflows/ci.yml": ("cue", "cue"),
        "distributions/npm/bin/ethos.mjs": ("prettier", "prettier"),
        "assets/brand/ethos-logo.svg": ("svgo", "svgo"),
        "assets/brand/ethos-logo-1024.png": ("source-binary", "pillow"),
        ".gitattributes": ("repository-canonical-text", "repository-hygiene"),
        ".config/checks/pytest/pytest.toml": ("taplo", "taplo"),
        "uv.lock": ("uv", "uv"),
    }
    for path, owners in expected.items():
        assignment = assignments[path]
        assert (assignment["format_owner"], assignment["validation_owner"]) == owners
    assert all("," not in entry["format_check"] for entry in assignments.values())
    assert assignments[".config/checks/pytest/pytest.toml"]["validation_command"].endswith(
        "-s config_quality"
    )
    adopter = init_git_repo(tmp_path / "adopter")
    provider_paths = (".github/workflows/ci.yml", ".gitlab-ci.yml")
    report = audit(adopter, paths=provider_paths, configuration=format_selection.CONFIG_PATH)
    assert report["verdict"] == "pass", report
    assert len(report["assignments"]) == len(provider_paths)
    assert all(
        (entry["format_owner"], entry["mutation_policy"]) == ("prettier", "native-formatter")
        for entry in report["assignments"]
    )
    declaration = adopter / ".config/checks/ci-projection/policy.toml"
    declaration.parent.mkdir(parents=True)
    declaration.write_text(
        'schema = "ethos-ci-template-consistency-v1"\n'
        '[[projection]]\nkind = "cue"\nprovider = "gitlab"\n'
        'projection = ".gitlab-ci.yml"\n'
        '[compiler]\nsource = ".config/ci/pipeline.cue"\n'
        'inputs = { gates = "system/gates.toml" }\n'
        'supply = { config = ".config/mise/config.toml", lock = ".config/mise/mise.lock" }\n'
    )
    projected = audit(adopter, paths=provider_paths, configuration=format_selection.CONFIG_PATH)
    owners = {entry["path"]: entry for entry in projected["assignments"]}
    assert projected["verdict"] == "pass", projected
    assert (
        owners[".gitlab-ci.yml"]["format_owner"],
        owners[".gitlab-ci.yml"]["mutation_policy"],
    ) == (
        "cue",
        "generator-only",
    )
    assert owners[".github/workflows/ci.yml"]["mutation_policy"] == "native-formatter"
    declaration.write_text("not = [valid\n")
    with pytest.raises(ValueError, match="projection_declaration_invalid"):
        audit(adopter, paths=provider_paths, configuration=format_selection.CONFIG_PATH)


def test_prettier_inputs_are_the_carriers_it_is_declared_to_own() -> None:
    """One native formatter respects producers and official artifact ownership."""
    tracked = tuple(filter(None, git(ROOT, "ls-files", "-z").split("\0")))
    assignments = audit(ROOT, paths=tracked)["assignments"]
    selected = {item["path"] for item in assignments if item["format_owner"] == "prettier"}
    assert "docs/README.md" in selected
    assert ".config/checks/pre-commit/.pre-commit-config.yaml" in selected
    assert ".gitlab-ci.yml" not in selected
    assert {"openspec/config.yaml", "openspec/specs/quality/spec.md"} <= selected
    assert any(path.startswith("openspec/changes/") for path in selected)
    assert not any(path.startswith("openspec/changes/archive/") for path in selected)
    assert "distributions/npm/bin/ethos.mjs" in selected


def test_markdown_lint_accepts_what_the_markdown_formatter_writes(tmp_path: Path) -> None:
    """Prettier writes underscore emphasis but asterisks inside a word; the lint accepts both."""
    root = init_git_repo(tmp_path / "repo")
    page = root / "docs" / "page.md"
    page.parent.mkdir()
    page.write_text("# Title\n\nintra*word*emphasis first, then an *emphasised* word.\n")
    formatted, ignored = render_source_content(root, "docs/page.md", "prettier", page.read_bytes())
    assert not ignored
    page.write_bytes(formatted)
    assert "then an _emphasised_ word" in page.read_text(encoding="utf-8")
    assert render_source_content(root, "docs/page.md", "prettier", formatted) == (
        formatted,
        False,
    )

    lint = run_command(
        root,
        (
            str(resolve_node_runtime().executable),
            str(product_node_module("markdownlint-cli2") / "markdownlint-cli2-bin.mjs"),
            "--config",
            str(ROOT / ".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml"),
            "docs/page.md",
        ),
        timeout=60,
        remove_env=("NODE_OPTIONS", "NODE_PATH"),
    )

    assert lint.returncode == 0, lint.stdout + lint.stderr


@pytest.mark.parametrize(
    ("home", "allowed"),
    [("src/ethos/adapters/", True), ("distributions/npm/", True), ("src/ethos/domain/", False)],
)
def test_native_javascript_transport_uses_its_semantic_adapter_home(
    tmp_path, monkeypatch, capsys, home, allowed
):
    root = init_git_repo(tmp_path / "repo")
    relative = ".config/checks/format-selection/policy.toml"
    config = root / relative
    config.parent.mkdir(parents=True)
    config.write_bytes((ROOT / relative).read_bytes())
    module = root / home / "example.mjs"
    module.parent.mkdir(parents=True)
    module.write_text("export {};\n")
    git(root, "add", relative, str(module.relative_to(root)))
    monkeypatch.setattr(format_selection, "ROOT", root)
    monkeypatch.setattr(format_selection, "CONFIG_PATH", config)
    assert format_selection.main() == (0 if allowed else 1)
    report = json.loads(capsys.readouterr().out)
    assert [item["path"] for item in report["failures"]] == (
        [] if allowed else [home + "example.mjs"]
    )
    assert all(
        item["reason"] == "format outside declared carrier home: .mjs"
        for item in report["failures"]
    )


@pytest.mark.parametrize(
    ("declaration", "error"),
    [
        ("format = 7\n", ValueError),
        ("[[format]]\nextensions = 7\n", TypeError),
        ("[policy]\nforbid_tracked_extensions = [7]\n", TypeError),
        ("[policy]\nunregistered_extension = 7\n", TypeError),
    ],
)
def test_format_selection_rejects_malformed_native_policy(
    tmp_path, monkeypatch, declaration: str, error: type[Exception]
) -> None:
    """A structurally invalid native declaration cannot be a quality pass."""
    config = tmp_path / "selection.toml"
    config.write_text(declaration)
    monkeypatch.setattr(format_selection, "CONFIG_PATH", config)
    monkeypatch.setattr(format_selection, "audit", lambda _root, **_kwargs: {})

    with pytest.raises(error):
        format_selection.main()


@pytest.mark.parametrize(
    "fields",
    [
        "validation_command = 7\nsemantic_companions = []",
        'validation_command = "ruff check"\nsemantic_companions = [7]',
    ],
)
def test_carrier_assignment_rejects_malformed_owned_fields(tmp_path, fields: str) -> None:
    """The producer, not each consumer, validates assignment field types."""
    config = tmp_path / ".config/checks/format-selection/policy.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        '[[ownership]]\npaths = ["example.py"]\nformat_owner = "ruff"\n'
        'format_command = "ruff format"\nformat_check = "ruff format --check"\n'
        'validation_owner = "ruff"\n'
        f'{fields}\nmutation_policy = "native-formatter"\n'
    )

    with pytest.raises(TypeError):
        audit(tmp_path, paths=("example.py",))


def test_unused_malformed_owner_cannot_hide_behind_a_valid_fallback(tmp_path) -> None:
    """Every declaration must be valid even when another owner covers the file."""
    config = tmp_path / ".config/checks/format-selection/policy.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        '[[ownership]]\nid = "valid"\npaths = ["example.py"]\n'
        'format_owner = "ruff"\nformat_command = "ruff format"\n'
        'format_check = "ruff format --check"\nvalidation_owner = "ruff"\n'
        'validation_command = "ruff check"\nmutation_policy = "native-formatter"\n'
        '\n[[ownership]]\nid = "ignored-invalid"\npaths = 7\n'
    )

    with pytest.raises(TypeError):
        audit(tmp_path, paths=("example.py",))


@pytest.mark.parametrize("name", ["accept", "reject"])
def test_native_vocabulary_has_one_executable_quality_owner(name: str) -> None:
    """Vale vocabulary parsing is configuration validation, not a prose waiver."""
    relative = f".config/checks/vale/styles/config/vocabularies/common/{name}.txt"
    report = audit(ROOT, paths=(relative,))

    assert report["verdict"] == "pass", report
    assert report["assignment_count"] == 1
    assignment = report["assignments"][0]
    assert assignment["validation_owner"] == "vale"
    assert assignment["validation_command"].endswith("-s config_quality")
    assert assignment["format_check"].endswith("-s repository_hygiene")
    assert assignment["mutation_policy"] == "canonical-text"
    assert audit(ROOT, paths=("docs/unowned.txt",))["verdict"] == "block"
