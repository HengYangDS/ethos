"""Status audit composition tests."""

import json
from pathlib import Path

import pytest

import ethos.domain.status as status
from tests.support.documentation import decision_fixture
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_paradigm_toolchain
from tests.support.paradigm import PARADIGM_OPENSPEC_CONFIG


def test_product_source_audit_does_not_observe_local_hook_runtime(
    monkeypatch, tmp_path: Path
) -> None:
    """Source correctness is independent of local mutation-runtime activation."""
    root = tmp_path / "repo"
    root.mkdir()
    profile = root / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text("", encoding="utf-8")
    tracked = ["README.md", "docs/concepts/kernel-model.md"]
    received: dict[str, object] = {}

    monkeypatch.setattr(
        status,
        "hook_runtime_binding",
        lambda _root: (_ for _ in ()).throw(AssertionError("hook runtime must not be observed")),
        raising=False,
    )
    monkeypatch.setattr(status, "git_files", lambda _root, _pattern: tracked)

    def repository_audit(_root: Path, **kwargs: object) -> dict[str, object]:
        received.update(kwargs)
        return {"verdict": "block"}

    monkeypatch.setattr(status.repository_audit_module, "repository_audit", repository_audit)

    assert status.product_audit(root) == {"verdict": "block"}
    assert "write_admission_gaps" not in received
    assert received["tracked_documents"] == tuple(tracked)


def _adopter(root: Path, *, registry: bool) -> Path:
    repo = init_git_repo(root)
    write_paradigm_toolchain(repo)
    git(repo, "add", ".config/mise")
    directory = repo / ".ethos"
    directory.mkdir()
    (directory / "profile.toml").write_text(
        'profile_id = "generic-repository"\n[openspec]\nmaterial_paths = ["**"]\n'
        + ('[proof]\ngate_registry = "gates.toml"\n' if registry else ""),
        encoding="utf-8",
    )
    (repo / "openspec/specs").mkdir(parents=True)
    (repo / "openspec/config.yaml").write_text(PARADIGM_OPENSPEC_CONFIG, encoding="utf-8")
    return repo


@pytest.mark.parametrize("registry", [False, True])
@pytest.mark.parametrize("shared", [False, True])
@pytest.mark.parametrize("condition", ["valid", "derived", "role", "release", "openspec", "commit"])
def test_common_adopter_audit_is_representation_independent(
    tmp_path: Path, monkeypatch, condition: str, *, registry: bool, shared: bool
) -> None:
    """Real generic observations never inherit product layout or skip obligations."""
    repo = _adopter(tmp_path / "node", registry=registry)
    if condition in {"valid", "derived", "role", "release"}:
        source = (
            "[invalid"
            if condition == "release"
            else '[protected_refs]\nbranches = ["dev"]\n'
            if condition == "role"
            else "[protected_refs]\ntags = []\n"
            if condition == "derived"
            else '[protected_refs]\nbranches = ["dev", "main"]\n'
        )
        (repo / ".ethos/release.toml").write_text(source, encoding="utf-8")
    elif condition == "openspec":
        (repo / "openspec/config.yaml").write_text("[invalid", encoding="utf-8")
    else:
        (repo / ".ethos/workspace.toml").write_text(
            '[commit_policy]\nsubject_pattern = "["\n', encoding="utf-8"
        )
    observation = status.openspec_shape_report(repo) if shared else None
    if shared:
        monkeypatch.setattr(status, "openspec_shape_report", lambda _: pytest.fail("second read"))
    report = status.audit_for_root(repo, openspec=observation)
    valid = condition in {"valid", "derived"}
    assert report["verdict"] == ("pass" if valid else "block"), report
    docs = report["docs"]
    assert isinstance(docs, dict)
    assert docs["document_count"] == 0
    assert "schemas" not in report
    if valid:
        release = report["release_policy"]
        assert isinstance(release, dict)
        protected = release["protected_refs"]
        assert isinstance(protected, dict)
        assert protected["branches"] == ["main", "dev"]
    else:
        fragment = {
            "role": "protected_branches_policy_missing",
            "release": "release_config_invalid",
            "openspec": "openspec_config_invalid",
            "commit": "commit_policy",
        }[condition]
        gaps = report["required_gaps"]
        assert isinstance(gaps, list)
        assert any(fragment in gap for gap in gaps)


def test_common_audit_does_not_require_optional_product_capabilities(tmp_path: Path) -> None:
    """A binding-only repository has no invented release, schema or doc obligation."""
    repo = _adopter(tmp_path / "minimal", registry=False)
    (repo / ".ethos/profile.toml").write_text('profile_id = "minimal"\n', encoding="utf-8")
    report = status.audit_for_root(repo)
    assert report["verdict"] == "pass", report
    release = report["release_policy"]
    assert isinstance(release, dict)
    assert release["declaration"] == {}
    assert release["protected_refs"] == {"branches": ["main", "dev"], "tags": []}
    openspec = report["openspec"]
    assert isinstance(openspec, dict)
    assert openspec["state"] == "not_applicable"


@pytest.mark.parametrize("registry", [False, True])
def test_common_audit_enforces_the_selected_documentation_owner(
    tmp_path: Path, *, registry: bool
) -> None:
    """A native docs root retains shared identity and navigation obligations."""
    repo = _adopter(tmp_path / "native-docs", registry=registry)
    profile = repo / ".ethos/profile.toml"
    profile.write_text(profile.read_text() + '\n[roots]\ndocs = "handbook"\n')
    handbook = repo / "handbook/rulings"
    handbook.mkdir(parents=True)
    decision = handbook / "dr-0006-supply-choice.md"
    decision.write_text(decision_fixture("DR-0006", subject="sample:supply-choice"))
    report = status.audit_for_root(repo)
    assert report["verdict"] == "pass", report
    assert report["docs"]["document_count"] == 0

    git(repo, "add", "--", "handbook")
    report = status.audit_for_root(repo)
    assert report["verdict"] == "pass", report
    assert report["docs"]["document_count"] == 1

    decision.rename(handbook / "supply-choice.md")
    git(repo, "add", "--all", "--", "handbook")
    report = status.audit_for_root(repo)
    assert report["verdict"] == "block", report
    gaps = report["required_gaps"]
    assert isinstance(gaps, list)
    assert "docs_decision_name_invalid:handbook/rulings/supply-choice.md" in gaps
    docs = report["docs"]
    assert isinstance(docs, dict)
    assert docs["document_count"] == 1

    (handbook / "supply-choice.md").rename(decision)
    git(repo, "add", "--all", "--", "handbook")
    assert status.audit_for_root(repo)["verdict"] == "pass"

    (handbook / "explanation.md").write_text(_document("sample:supply", "explanation", "Supply"))
    git(repo, "add", "--", "handbook")
    report = status.audit_for_root(repo)
    gaps = report["required_gaps"]
    assert isinstance(gaps, list)
    assert report["verdict"] == "block", report
    assert "docs_readme_missing:handbook/rulings/README.md" in gaps
    (handbook / "README.md").write_text(
        _document("sample:rulings", "index", "Rulings")
        + "\nRead [the choice](dr-0006-supply-choice.md) and [explanation](explanation.md).\n"
    )
    git(repo, "add", "--", "handbook")
    assert status.audit_for_root(repo)["verdict"] == "pass"

    (handbook / "unselected.md").write_text("malformed residue\n")
    assert status.audit_for_root(repo)["verdict"] == "pass"


def test_public_common_gate_cannot_omit_documentation_identity(tmp_path: Path) -> None:
    """Default governance refuses a docs defect without a separately selected docs gate."""
    repo = _adopter(tmp_path / "public-docs", registry=False)
    decision = repo / "docs/rulings/choice.md"
    decision.parent.mkdir(parents=True)
    decision.write_text(_document("sample:choice", "decision", "Choice"))
    commit_fixture(repo, "docs: preserve a decision choice")

    observed = run_ethos_raw(
        "prove", "--host", "--execute", "--gate", "repository-audit", "--json", cwd=repo
    )
    report = json.loads(observed.stdout)

    assert observed.returncode != 0
    assert report["verdict"] == "block", report
    assert report["summary"]["proof_attestation_issued"] is False
    payload = json.loads(report["data"]["checks"][0]["stdout"])
    audit = payload["providers"][0]["report"]
    assert "docs_decision_name_invalid:docs/rulings/choice.md" in audit["required_gaps"]


def _document(subject: str, role: str, title: str) -> str:
    """Supply a complete native metadata and visible reading fixture."""
    return (
        f"---\nsubject: {subject}\nrole: {role}\nstate: canonical\nrelations: {{}}\n"
        f"---\n\n# {title}\n\nStatus: canonical.\n\nPurpose: explain one choice.\n"
    )
