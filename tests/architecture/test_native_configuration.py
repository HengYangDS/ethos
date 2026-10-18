"""Native configuration selection binds each input to its declared consumer."""

from __future__ import annotations

from pathlib import Path

import pytest

import ethos.adapters.gates.configuration as config_quality
from tests.support.governed_repository import PARADIGM_FORMATTERS
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

ROOT = Path(__file__).resolve().parents[2]


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
    # The fixture's TOML formatter bindings are not this YAML selection case's subject.
    git(root, "rm", "-q", *PARADIGM_FORMATTERS)
    policy = root / ".config/checks/format-selection/policy.toml"
    policy.parent.mkdir(parents=True)
    policy.write_bytes((ROOT / policy.relative_to(root)).read_bytes())
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
    (root / ".gitignore").write_text(
        policy.relative_to(root).as_posix() + "\n" + (relative if state == "ignored" else "")
    )
    if state not in {"ignored", "untracked", "missing"}:
        git(root, "add", relative)
    if state in {"missing", "deleted"}:
        target.unlink()
    spellings = (
        (relative, str(target), str(root / ".config" / ".." / relative)) if explicit else (None,)
    )
    for spelling in spellings:
        report = config_quality.configuration_report(root, paths=(spelling,) if spelling else ())
        failures = report["required_gaps"]
        assert isinstance(failures, list)
        assert bool(failures) is fails, failures
        if fails:
            assert relative in "\n".join(failures)
            assert state != "external" or "another owner" in "\n".join(failures)


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("state", ["valid", "malformed", "missing"])
def test_native_configuration_compiles_declared_vale_vocabulary(
    tmp_path: Path, state: str, *, explicit: bool
) -> None:
    """The real locked parser rejects bad or absent inputs without rewriting them."""
    root = init_git_repo(tmp_path / "repo")
    git(root, "rm", "-q", *PARADIGM_FORMATTERS)
    policy = root / ".config/checks/format-selection/policy.toml"
    policy.parent.mkdir(parents=True)
    policy.write_bytes((ROOT / policy.relative_to(root)).read_bytes())
    (root / ".gitignore").write_text(policy.relative_to(root).as_posix() + "\n")
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

    report = config_quality.configuration_report(
        root, paths=(str(accepted.relative_to(root)),) if explicit else ()
    )
    failures = report["required_gaps"]
    assert isinstance(failures, list)

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
    git(root, "rm", "-q", *PARADIGM_FORMATTERS)
    policy = root / ".config/checks/format-selection/policy.toml"
    policy.parent.mkdir(parents=True)
    policy.write_bytes((ROOT / policy.relative_to(root)).read_bytes())
    (root / ".gitignore").write_text(policy.relative_to(root).as_posix() + "\n")
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

    report = config_quality.configuration_report(
        root, paths=(str(unselected.relative_to(root)),) if explicit else ()
    )
    failures = report["required_gaps"]
    assert isinstance(failures, list)

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
    git(root, "rm", "-q", *PARADIGM_FORMATTERS)
    policy = root / ".config/checks/format-selection/policy.toml"
    policy.parent.mkdir(parents=True)
    policy.write_bytes((ROOT / policy.relative_to(root)).read_bytes())
    (root / ".gitignore").write_text(policy.relative_to(root).as_posix() + "\n")
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

    report = config_quality.configuration_report(root, paths=(str(additional.relative_to(root)),))
    failures = report["required_gaps"]
    assert isinstance(failures, list)

    assert bool(failures) is (state == "malformed"), failures
    if failures:
        assert "E100" in "\n".join(failures)
    assert {path: path.read_bytes() for path in inputs} == original
    assert not (common.parent / "reject.txt").exists()
    assert not (additional.parent / "reject.txt").exists()
    assert not (root / "build").exists()
