"""Native formatting and semantic configuration validation share exact authored inputs."""

from __future__ import annotations

from pathlib import Path

import pytest
import tomli_w

import ethos.adapters.gates.configuration as configuration
from ethos.adapters.gates.configuration import configuration_report
from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module
from ethos.normalization.coercion import string_sequence
from ethos.repository.release.resources import canonical_resource
from tests.support.governed_repository import committed_source_repo
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.subprocesses import completed

VALE_FAILED = "Vale configuration validation failed: Vale native"
VALE_VOCABULARY = '{"Paths": [], "Vocabularies": {"A": 0}, "Vocab": []}'


@pytest.mark.parametrize(
    ("relative", "content"),
    [
        ("source.json", '{ "values": [1, 2], "nested": { "valid": true } }\n'),
        ("source.yaml", "value: [one, two]\n"),
        (".gitlab-ci.yml", "value: [one, two]\n"),
        (".github/workflows/ci.yml", "value: [one, two]\n"),
        ("source.yaml", "command: " + "word " * 48 + "end\n"),
        ("source.yaml", "value: |\n  first\n\n\n  second\n"),
        ("source.toml", '"$schema" = "https://schema.invalid/never.json"\nvalue = 1\n'),
        (".config/checks/taplo/taplo.toml", "#:schema https://schema.invalid/never.json\n"),
    ],
)
def test_native_accepted_configuration_passes_offline_and_preserves_its_bytes(
    tmp_path: Path, relative: str, content: str
) -> None:
    root = init_git_repo(tmp_path / "repo")
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    report = configuration_report(root, paths=(relative,))
    assert report["verdict"] == "pass", report
    assert report["file_count"] == 1
    assert path.read_text() == content


@pytest.mark.parametrize(
    "relative", ["source.json", "source.yaml", ".gitlab-ci.yml", ".github/workflows/ci.yml"]
)
def test_native_format_refusal_is_not_a_write(tmp_path: Path, relative: str) -> None:
    root = init_git_repo(tmp_path / "repo")
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    content = '{"value":true}\n' if relative.endswith("json") else "value: [ one,two ]\n"
    path.write_text(content)
    report = configuration_report(root, paths=(relative,))
    assert report["verdict"] == "block", report
    assert report["required_gaps"]
    assert path.read_text() == content


@pytest.mark.parametrize(
    ("content", "diagnostic"),
    [("value: 1\nvalue: 2\n", "key-duplicates"), ("value: *missing\n", "undeclared alias")],
)
def test_native_semantic_yaml_rejects_invalid_relations_without_layout_policy(
    tmp_path: Path,
    content: str,
    diagnostic: str,
) -> None:
    root = init_git_repo(tmp_path / "repo")
    (root / "source.yaml").write_text(content)
    report = configuration_report(root, paths=("source.yaml",))
    assert report["verdict"] == "block", report
    assert diagnostic in str(report["required_gaps"])
    assert (root / "source.yaml").read_text() == content


def test_native_dependency_resolution_keeps_its_byte_owner(tmp_path: Path) -> None:
    root = init_git_repo(tmp_path / "repo")
    baseline = configuration_report(root)
    relative = ".mise/locks/npm/fixture/aube-lock.yaml"
    path = root / relative
    path.parent.mkdir(parents=True)
    content = "producer-owned: [ x,y ]\n"
    path.write_text(content)
    git(root, "add", relative)
    report = configuration_report(root)
    assert report["verdict"] == baseline["verdict"] == "pass", report
    assert report["file_count"] == baseline["file_count"], report
    refused = configuration_report(root, paths=(relative,))
    assert refused["verdict"] == "block"
    assert "another owner" in str(refused["required_gaps"])
    assert path.read_text() == content


@pytest.mark.parametrize(
    "relative", ["source.json", "source.yaml", ".gitlab-ci.yml", ".github/workflows/ci.yml"]
)
def test_native_formatter_fix_and_check_are_one_idempotent_path(
    tmp_path: Path, relative: str
) -> None:
    root = init_git_repo(tmp_path / "repo")
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    content = '{"value":true}\n' if relative.endswith("json") else "value: [ one,two ]\n"
    path.write_text(content)
    command = (
        str(resolve_node_runtime().executable),
        str(product_node_module("prettier") / "bin/prettier.cjs"),
        "--config",
        str(canonical_resource(".config/checks/prettier/prettier.toml")),
        "--no-editorconfig",
        "--write",
        "--",
        relative,
    )
    assert configuration_report(root, paths=(relative,))["verdict"] == "block"
    run_command(root, command, timeout=30, check=True, remove_env=("NODE_OPTIONS", "NODE_PATH"))
    accepted = path.read_bytes()
    assert accepted != content.encode()
    assert configuration_report(root, paths=(relative,))["verdict"] == "pass"
    run_command(root, command, timeout=30, check=True, remove_env=("NODE_OPTIONS", "NODE_PATH"))
    assert path.read_bytes() == accepted
    assert configuration_report(root, paths=(relative,))["verdict"] == "pass"


def test_configuration_owner_preserves_the_common_floor_and_exact_inputs(tmp_path) -> None:
    """Local ignores and ambient configuration cannot weaken installed native checks."""
    root = init_git_repo(tmp_path / "repo")
    yaml_policy = root / ".config/checks/yamllint/.yamllint.yaml"
    yaml_policy.parent.mkdir(parents=True)
    yaml_policy.write_text("---\nextends: default\nignore: '*.yaml'\n")
    yaml_input = root / "example.yaml"
    toml_input = root / "example.toml"
    json_input = root / "example.json"
    ini_input = root / "example.ini"
    git(root, "add", yaml_policy.relative_to(root).as_posix())
    cases = (
        (yaml_input, "---\nvalue: true\n", "pass"),
        (yaml_input, "---\nvalue: true\n\n\nother: 1\n", "block"),
        (toml_input, 'value = "valid"\n', "pass"),
        (toml_input, 'value="valid"\n', "block"),
        (json_input, '{\n  "value": true\n}\n', "pass"),
        (json_input, '{"value":true}\n', "block"),
        (ini_input, "[native]\nvalue = valid\n", "pass"),
        (ini_input, "[native]\nvalue = first\nvalue = duplicate\n", "block"),
    )
    for target, content, verdict in cases:
        target.write_text(content)
        report = configuration_report(root, paths=(target.name,))
        assert (report["verdict"], target.read_text()) == (verdict, content), report
    invalid_policy = "rules:\n  missing-native-rule: enable\n"
    yaml_policy.write_text(invalid_policy)
    yaml_input.write_text("---\nvalue: true\n")
    report = configuration_report(root, paths=(yaml_input.name,))
    assert report["verdict"] == "block", report
    assert report["required_gaps"]
    assert yaml_policy.read_text() == invalid_policy
    assert yaml_input.read_text() == "---\nvalue: true\n"


def test_configuration_owner_validates_native_formatter_policy_before_checking(tmp_path) -> None:
    """Original formatter rejects malformed native policy and preserves authored bytes."""
    root = init_git_repo(tmp_path / "repo")
    target = root / "example.json"
    content = '{\n  "value": true\n}\n'
    target.write_text(content)
    policy = root / ".config/checks/prettier/prettier.toml"
    policy.parent.mkdir(parents=True, exist_ok=True)
    git(root, "add", target.name)
    for declaration, verdict in (
        ({"tabWidth": 2}, "pass"),
        ({"tabWidth": "unknown"}, "block"),
        ({"tabWidth": True}, "block"),
        ({"unknownFormat": True}, "block"),
    ):
        original = tomli_w.dumps(declaration)
        policy.write_text(original)
        git(root, "add", policy.relative_to(root).as_posix())
        report = configuration_report(root, paths=(target.name,))
        assert (report["verdict"], target.read_text(), policy.read_text()) == (
            verdict,
            content,
            original,
        ), report
        assert bool(report["required_gaps"]) == (verdict == "block"), report


@pytest.mark.parametrize(
    ("state", "explicit", "fails"),
    [
        ("invalid", False, True),
        ("invalid", True, True),
        ("valid", False, False),
        ("valid", True, False),
        ("scalar", True, False),
        ("blank", True, True),
        ("missing", True, True),
        ("deleted", False, False),
        ("deleted", True, True),
        ("untracked", False, True),
        ("ignored", False, False),
        ("external", False, False),
        ("external", True, True),
    ],
)
def test_config_selection_keeps_native_failures_and_ownership(tmp_path, state, explicit, fails):
    """Default discovery covers candidates; explicit absent or foreign inputs cannot pass."""
    root = init_git_repo(tmp_path / "repo")
    (root / ".config").mkdir(exist_ok=True)
    relative = "openspec/config.yaml" if state == "external" else ".config/new-policy.yaml"
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        {
            "valid": "---\nvalue: true\n",
            "scalar": "---\nvalue: |\n  first\n\n\n  second\n",
            "blank": "---\nfirst: 1\n\n\nsecond: 2\n",
        }.get(state, "broken: [\n")
    )
    (root / ".gitignore").write_text(relative if state == "ignored" else "")
    if state not in {"ignored", "untracked", "missing"}:
        git(root, "add", relative)
    if state in {"missing", "deleted"}:
        target.unlink()
    spellings = (
        (relative, str(target), str(root / ".config" / ".." / relative)) if explicit else (None,)
    )
    for spelling in spellings:
        report = configuration_report(root, paths=(spelling,) if spelling else ())
        failures = string_sequence(report["required_gaps"])
        assert bool(failures) is fails, failures
        if fails:
            assert relative in "\n".join(failures)
            assert state != "external" or "another owner" in "\n".join(failures)


def test_configuration_leads_with_the_refusal_of_each_input(tmp_path: Path) -> None:
    """Unsupported, escaping, unterminated or unparsable inputs lead the gaps with their cause."""
    root = init_git_repo(tmp_path / "repo")
    for relative, content, gap in (
        ("a.py", "", "unsupported config lint targets: a.py"),
        ("../a.json", "", "config target outside repository: ../a.json"),
        ("a.toml", "a = 1", "a.toml: missing final newline"),
        ("a.toml", "a = 1\n\n", "a.toml: more than one trailing newline"),
        ("a.toml", "a = [\n", "a.toml: TOML parse failed: "),
        ("a.json", "{\n", "a.json: JSON parse failed: "),
    ):
        (root / relative).write_text(content)
        gaps = string_sequence(configuration_report(root, paths=(relative,))["required_gaps"])
        assert gaps[0].startswith(gap), gaps


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("state", ["valid", "malformed", "missing"])
def test_native_configuration_compiles_declared_vale_vocabulary(
    tmp_path: Path, state: str, *, explicit: bool
) -> None:
    """The real locked parser rejects bad or absent inputs without rewriting them."""
    root = init_git_repo(tmp_path / "repo")
    config = root / ".config/checks/vale/vale.ini"
    config.parent.mkdir(parents=True)
    config.write_text(
        "[DEFAULT]\nStylesPath = styles\nVocab = Common\nMinAlertLevel = error\n"
        "\n[*.md]\nBasedOnStyles = Vale\n"
    )
    vocabulary = config.parent / "styles/config/vocabularies/Common"
    vocabulary.mkdir(parents=True)
    accepted, rejected = vocabulary / "accept.txt", vocabulary / "reject.txt"
    accepted.write_text("(?i:invalid\n" if state == "malformed" else "(?i:prewrite)\n")
    rejected.write_text("Github\n")
    inputs = (config, accepted, rejected)
    git(root, "add", *(str(path.relative_to(root)) for path in inputs))
    if state == "missing":
        accepted.unlink()
    original = {path: path.read_bytes() for path in inputs if path.exists()}

    report = configuration_report(
        root, paths=(str(accepted.relative_to(root)),) if explicit else ()
    )
    failures = string_sequence(report["required_gaps"])

    assert bool(failures) is (state != "valid"), failures
    if state == "malformed":
        assert "E100" in "\n".join(failures)
    if state == "missing":
        assert "accept" in "\n".join(failures)
    assert {path: path.read_bytes() for path in original} == original
    assert accepted.exists() is (state != "missing")
    assert not (root / "build").exists()


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("content", ["prewrite\n", "(?i:invalid\n"], ids=["valid", "malformed"])
def test_configuration_refuses_vocabulary_without_native_consumer(
    tmp_path: Path, content: str, *, explicit: bool
) -> None:
    """Owned vocabulary inputs cannot pass through an unrelated native selection."""
    root = init_git_repo(tmp_path / "repo")
    config = root / ".config/checks/vale/vale.ini"
    config.parent.mkdir(parents=True)
    config.write_text(
        "[DEFAULT]\nStylesPath = styles\nVocab = Common\nMinAlertLevel = error\n"
        "\n[*.md]\nBasedOnStyles = Vale\n"
    )
    selected = config.parent / "styles/config/vocabularies/Common/accept.txt"
    selected.parent.mkdir(parents=True)
    selected.write_text("prewrite\n")
    unselected = config.parent / "styles/config/vocabularies/Unselected/accept.txt"
    unselected.parent.mkdir(parents=True)
    unselected.write_text(content)
    inputs = (config, selected, unselected)
    git(root, "add", *(str(path.relative_to(root)) for path in inputs))
    original = {path: path.read_bytes() for path in inputs}

    report = configuration_report(
        root, paths=(str(unselected.relative_to(root)),) if explicit else ()
    )
    failures = string_sequence(report["required_gaps"])

    assert failures, "The native configuration never consumed the selected vocabulary."
    assert str(unselected.relative_to(root)) in "\n".join(failures)
    assert "not consumed" in "\n".join(failures)
    assert {path: path.read_bytes() for path in inputs} == original
    assert not (selected.parent / "reject.txt").exists()
    assert not (root / "build").exists()


@pytest.mark.parametrize("state", ["valid", "malformed"])
@pytest.mark.parametrize("default_vocabulary", [False, True])
def test_native_configuration_compiles_section_vocabulary_without_optional_files(
    tmp_path: Path, state: str, *, default_vocabulary: bool
) -> None:
    """Section-selected vocabulary is compiled without inventing optional inputs."""
    root = init_git_repo(tmp_path / "repo")
    config = root / ".config/checks/vale/vale.ini"
    config.parent.mkdir(parents=True)
    config.write_text(
        "[DEFAULT]\nStylesPath = styles\n"
        + ("Vocab = Common\n" if default_vocabulary else "")
        + "MinAlertLevel = error\n"
        "\n[*.md]\nBasedOnStyles = Vale\n\n[docs/*.md]\nVocab = Additional\n"
    )
    common = config.parent / "styles/config/vocabularies/Common/accept.txt"
    common.parent.mkdir(parents=True)
    common.write_text("prewrite\n")
    additional = config.parent / "styles/config/vocabularies/Additional/accept.txt"
    additional.parent.mkdir(parents=True)
    additional.write_text("(?i:invalid\n" if state == "malformed" else "semantics\n")
    inputs = (config, common, additional)
    git(root, "add", *(str(path.relative_to(root)) for path in inputs))
    original = {path: path.read_bytes() for path in inputs}

    report = configuration_report(root, paths=(str(additional.relative_to(root)),))
    failures = string_sequence(report["required_gaps"])

    assert bool(failures) is (state == "malformed"), failures
    if failures:
        assert "E100" in "\n".join(failures)
    assert {path: path.read_bytes() for path in inputs} == original
    assert not (common.parent / "reject.txt").exists()
    assert not (additional.parent / "reject.txt").exists()
    assert not (root / "build").exists()


@pytest.mark.parametrize(
    ("stdout", "stderr", "gap"),
    [
        ("[]", "", f"{VALE_FAILED} configuration is unobservable"),
        (VALE_VOCABULARY, "", f"{VALE_FAILED} vocabulary directory is unobservable: A"),
        ("", "W100 native warning", "W100 native warning"),
    ],
)
def test_unusable_native_vale_observation_is_a_gap(tmp_path, monkeypatch, stdout, stderr, gap):
    """Native Vale diagnostics, or output that cannot bind its vocabularies, block the check."""
    root = committed_source_repo(tmp_path, {".config/checks/vale/vale.ini": ""})
    monkeypatch.setattr(configuration, "resolve_native_tool", Path)
    monkeypatch.setattr(configuration, "run_command", lambda *_a, **_k: completed(stdout, stderr))
    report = configuration_report(root, paths=(".config/checks/vale/vale.ini",))
    assert report["required_gaps"] == [gap], report
