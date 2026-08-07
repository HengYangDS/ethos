from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos.repository.policy.gates import resolve_gate_policy
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import profile_evidence_roots
from ethos.repository.profile import profile_root
from ethos.repository.profile import render_repository_profile


def test_profile_contract_is_strict_frozen_and_deterministic(tmp_path: Path) -> None:
    declaration = RepositoryProfileDeclaration.bootstrap('sample<repo&"')

    rendered = render_repository_profile(declaration)

    assert rendered == 'profile_id = "sample<repo&\\""\n'
    assert declaration.commitment == ".ethos/commitment.toml"
    assert declaration.openspec is None
    with pytest.raises(ValidationError):
        declaration.profile_id = "mutable"
    with pytest.raises(TypeError):
        declaration.proof.code_correctness_map["behavior"] = "mutable"
    with pytest.raises(ValidationError):
        RepositoryProfileDeclaration.model_validate(
            {
                "profile_id": "sample",
                "extra": True,
            }
        )

    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(rendered, encoding="utf-8")
    loaded = load_repository_profile(tmp_path)

    assert loaded.state == "valid"
    assert loaded.declaration is not None
    assert loaded.declaration.profile_id == 'sample<repo&"'
    assert loaded.declaration.commitment == ".ethos/commitment.toml"
    assert loaded.declaration.openspec is None


def test_profile_can_explicitly_select_commitment_and_openspec_carriers(tmp_path: Path) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        'profile_id = "self"\n'
        'commitment = "governance/commitment.toml"\n\n'
        "[openspec]\n"
        'material_paths = ["docs/**"]\n\n'
        "[proof]\n"
        'gate_registry = "system/gates.toml"\n',
        encoding="utf-8",
    )

    declaration = load_repository_profile(tmp_path).declaration

    assert declaration is not None
    assert declaration.commitment == "governance/commitment.toml"
    assert declaration.openspec is not None
    assert declaration.openspec.material_paths == ("docs/**",)
    assert declaration.proof.gate_registry == "system/gates.toml"


@pytest.mark.parametrize(
    "proof",
    [
        'required_gates = ["tests", "types"]\n',
        'code_axes = { behavior = "tests", static-analysis = "types" }\n',
        (
            'code_correctness_gates = ["tests", "types"]\n\n'
            '[proof.code_correctness_map]\nbehavior = "tests"\n'
        ),
        (
            'code_correctness_gates = ["tests", "types"]\n\n'
            "[proof.code_correctness_map]\n"
            'behavior = "tests"\nstatic-analysis = "tests"\n'
        ),
    ],
)
def test_profile_rejects_retired_or_incomplete_proof_owners(tmp_path: Path, proof: str) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text('profile_id = "sample"\n\n[proof]\n' + proof, encoding="utf-8")

    assert load_repository_profile(tmp_path).state == "invalid"


def test_real_adopter_profile_is_identical_from_worktree_and_commit(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", tmp_path], check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True
    )
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        'profile_id = "codex-responses-proxy"\n\n'
        "[proof]\n"
        'code_correctness_gates = ["python-quality", "python-matrix"]\n\n'
        "[proof.code_correctness_map]\n"
        'behavior = "python-matrix"\n'
        'static-analysis = "python-quality"\n\n'
        "[[proof.gates]]\n"
        'id = "python-quality"\n'
        'kind = "static"\n'
        'command = ["nox", "-s", "quality"]\n'
        'dimensions = ["static-analysis"]\n'
        'execution_mode = "subprocess"\n'
        'evidence_class = "proof"\n'
        "trust_bearing = true\n"
        'tool_adapter = "repository-native"\n\n'
        "[[proof.gates]]\n"
        'id = "python-matrix"\n'
        'kind = "test"\n'
        'command = ["nox", "-s", "tests"]\n'
        'dimensions = ["behavior"]\n'
        'execution_mode = "subprocess"\n'
        'evidence_class = "proof"\n'
        "trust_bearing = true\n"
        'tool_adapter = "repository-native"\n',
        encoding="utf-8",
    )
    subprocess.run(["git", "add", ".ethos/profile.toml"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "profile"], cwd=tmp_path, check=True)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    worktree = resolve_gate_policy(tmp_path)
    committed = resolve_gate_policy(tmp_path, tree_ref=head)

    assert worktree.profile is not None
    assert worktree.profile.state == "valid"
    assert worktree.digest == committed.digest
    assert set(worktree.gate_ids) == {"python-quality", "python-matrix"}


def test_profile_gate_cannot_select_registry_projection(tmp_path: Path) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        'profile_id = "sample"\n\n'
        "[proof]\n"
        'code_correctness_gates = ["tests"]\n\n'
        "[[proof.gates]]\n"
        'id = "tests"\n'
        'kind = "test"\n'
        'command = ["pytest"]\n'
        'registries = ["quality"]\n',
        encoding="utf-8",
    )

    assert load_repository_profile(tmp_path).state == "invalid"


@pytest.mark.parametrize(
    "text",
    [
        "profile_id = ''\n[openspec]\nmaterial_paths = ['openspec/**']\n",
        "profile_id = 'sample'\n[openspec]\nmaterial_paths = []\n",
        "profile_id = 'sample'\n[openspec]\nmaterial_paths = ['/absolute']\n",
        (
            "profile_id = 'sample'\n[openspec]\nmaterial_paths = ['openspec/**']\n"
            "[roots]\ndurable_evidence = '../evidence'\n"
        ),
        (
            "profile_id = 'sample'\n[openspec]\nmaterial_paths = ['openspec/**']\n"
            "[roots]\ndocs = '/docs'\n"
        ),
        (
            "profile_id = 'sample'\n[openspec]\nmaterial_paths = ['openspec/**']\n"
            "[roots]\nrules = 'rules\\\\windows'\n"
        ),
        (
            "profile_id = 'sample'\n[openspec]\nmaterial_paths = ['openspec/**']\n"
            "[roots]\nlocal_state = 'runtime'\n"
        ),
        (
            "profile_id = 'sample'\n[openspec]\nmaterial_paths = ['openspec/**']\n"
            "[evidence]\ndurable_roots = ['../outside']\n"
        ),
        (
            "profile_id = 'sample'\n[openspec]\nmaterial_paths = ['openspec/**']\n"
            "[external_backend]\nstate = 'default'\n"
            "minimum_version = 'successor>=incumbent'\n"
            "control = 'control.toml'\nretirement_policy = 'retirement.toml'\n"
        ),
        (
            "profile_id = 'sample'\n[openspec]\nmaterial_paths = ['openspec/**']\n"
            "[embedded_backend]\nstate = 'frozen'\n"
            "minimum_version = 'incumbent'\n"
            "control = 'control.toml'\nretirement_policy = 'retirement.toml'\n"
        ),
        (
            "profile_id = 'sample'\n[openspec]\nmaterial_paths = ['openspec/**']\n"
            "[rollback_window]\nstate = 'complete'\n"
            "evidence_manifest = 'rollback.toml'\n"
            "completed_scenarios = ['proof_report']\n"
            "required_scenarios = ['proof_report']\n"
        ),
        "profile_id = 'sample'\n[openspec]\nmaterial_paths = ['openspec/**']\nextra = true\n",
    ],
)
def test_profile_contract_rejects_incomplete_or_undeclared_shape(tmp_path: Path, text: str) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(text, encoding="utf-8")

    assert load_repository_profile(tmp_path).state == "invalid"


def test_profile_contract_rejects_non_string_paths() -> None:
    with pytest.raises(TypeError, match="repository path must be a string"):
        RepositoryProfileDeclaration.model_validate(
            {
                "profile_id": "sample",
                "openspec": {"material_paths": ["openspec/**"]},
                "roots": {"durable_evidence": 1},
            }
        )


def test_profile_contract_rejects_complete_former_envelope(tmp_path: Path) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        "schema_version = 1\n"
        'profile_id = "sample"\n'
        'profile_version = "1"\n'
        'ethos_contract_version = "1"\n\n'
        "[repository]\n"
        'kind = "documentation"\n'
        'root_subject = "sample"\n\n'
        "[openspec]\n"
        'material_paths = ["openspec/**"]\n',
        encoding="utf-8",
    )

    assert load_repository_profile(tmp_path).state == "invalid"


def test_current_profile_rejects_root_rules_workaround(tmp_path: Path) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        'profile_id = "sample"\n\n'
        "[roots]\n"
        'rules = "."\n\n'
        "[openspec]\n"
        'material_paths = ["openspec/**"]\n',
        encoding="utf-8",
    )

    assert load_repository_profile(tmp_path).state == "invalid"


def test_profile_includes_declared_normative_sources_without_root_escape(tmp_path: Path) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        'profile_id = "sample"\n\nnormative_sources = ["guidelines.md"]\n',
        encoding="utf-8",
    )

    assert profile_evidence_roots(tmp_path) == (
        ".ethos/profile.toml",
        ".ethos/commitment.toml",
        "rules",
        "guidelines.md",
        "evidence",
        "docs",
    )


def test_profile_loader_rejects_unreadable_profile(tmp_path: Path, monkeypatch) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text("profile_id = 'sample'\n", encoding="utf-8")
    original = Path.read_text

    def unreadable(path: Path, *args, **kwargs) -> str:
        if path == profile.resolve():
            raise OSError
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable)

    assert load_repository_profile(tmp_path).state == "invalid"


def test_invalid_profile_never_falls_back_to_default_roots(tmp_path: Path) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        "profile_id = 'sample'\n[roots]\ndurable_evidence = '../evidence'\n",
        encoding="utf-8",
    )

    loaded = load_repository_profile(tmp_path)

    assert loaded.state == "invalid"
    with pytest.raises(ValueError, match="repository_profile_invalid"):
        profile_root(tmp_path, "durable_evidence")


def test_profile_loader_never_falls_back_from_an_invalid_tree_ref(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", tmp_path], check=True)
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text("profile_id = 'working-tree'\n", encoding="utf-8")

    with pytest.raises(ValueError, match="repository_tree_ref_invalid"):
        load_repository_profile(tmp_path, tree_ref="deadbeef" * 5)
