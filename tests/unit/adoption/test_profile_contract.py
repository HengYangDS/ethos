"""Validate immutable adopter profiles without fallback from invalid selected state."""

from __future__ import annotations

from pathlib import Path

import pytest
import tomli_w
from pydantic import ValidationError

from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.profile import load_committed_repository_profile
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import profile_root
from ethos.repository.profile import render_repository_profile
from tests.support.governed_repository import git
from tests.support.literal_cases import literal_case


def _write_profile(root: Path, text: str) -> Path:
    profile = root / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(text, encoding="utf-8")
    return profile


def _assert_invalid_profile(root: Path, text: str) -> None:
    _write_profile(root, text)
    assert load_repository_profile(root).state == "invalid"


def test_profile_contract_is_strict_frozen_and_deterministic(tmp_path: Path) -> None:
    declaration = RepositoryProfileDeclaration.bootstrap('sample<repo&"')

    rendered = render_repository_profile(declaration)

    assert rendered == 'profile_id = "sample<repo&\\""\n'
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

    _write_profile(tmp_path, rendered)
    loaded = load_repository_profile(tmp_path)

    assert loaded.state == "valid"
    assert loaded.declaration is not None
    assert loaded.declaration.profile_id == 'sample<repo&"'
    assert loaded.declaration.openspec is None


@pytest.mark.parametrize(
    "fields",
    [
        {"roots": {"durable_evidence": "evidence"}},
        {"evidence": {"durable_roots": ["evidence"]}},
    ],
)
def test_profile_cannot_select_current_proof_by_directory(fields) -> None:
    """Retired directory declarations cannot become a parallel proof selector."""
    with pytest.raises(ValidationError):
        RepositoryProfileDeclaration.model_validate({"profile_id": "sample", **fields})


@pytest.mark.parametrize(
    "proof",
    literal_case(
        "adoption.test_profile_contract:parametrize:test_profile_rejects_retired_or_incomplete_proof_owners:0"
    ),
)
def test_profile_rejects_retired_or_incomplete_proof_owners(tmp_path: Path, proof: str) -> None:
    _assert_invalid_profile(tmp_path, 'profile_id = "sample"\n\n[proof]\n' + proof)


def test_adopter_profile_is_identical_from_worktree_and_commit(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "test")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    cases = (
        ("python-quality", "static", "quality", "static-analysis"),
        ("python-matrix", "test", "tests", "behavior"),
    )
    gates = [
        {
            "id": name,
            "kind": kind,
            "command": ["nox", "-s", command],
            "dimensions": [dimension],
            "execution_mode": "subprocess",
            "evidence_class": "proof",
            "trust_bearing": True,
            "tool_adapter": "repository-native",
        }
        for name, kind, command, dimension in cases
    ]
    _write_profile(
        tmp_path,
        tomli_w.dumps(
            {
                "profile_id": "native-check-adopter",
                "proof": {
                    "code_correctness_gates": [row[0] for row in cases],
                    "code_correctness_map": {row[3]: row[0] for row in cases},
                    "gates": gates,
                },
            }
        ),
    )
    git(tmp_path, "add", ".ethos/profile.toml")
    git(tmp_path, "commit", "-q", "-m", "profile")
    head = git(tmp_path, "rev-parse", "HEAD")

    worktree = resolve_gate_policy(tmp_path)
    committed = resolve_gate_policy(tmp_path, tree_ref=head)

    assert worktree.profile is not None
    assert worktree.profile.state == "valid"
    assert worktree.digest == committed.digest
    assert set(worktree.gate_ids) == {"python-quality", "python-matrix"}


def test_profile_gate_rejects_retired_registry_projection_field(tmp_path: Path) -> None:
    _assert_invalid_profile(
        tmp_path,
        'profile_id = "sample"\n\n'
        "[proof]\n"
        'code_correctness_gates = ["tests"]\n\n'
        "[[proof.gates]]\n"
        'id = "tests"\n'
        'kind = "test"\n'
        'command = ["pytest"]\n'
        'registries = ["quality"]\n',
    )


@pytest.mark.parametrize(
    "text",
    literal_case(
        "adoption.test_profile_contract:parametrize:test_profile_contract_rejects_incomplete_or_undeclared_shape:1"
    ),
)
def test_profile_contract_rejects_incomplete_or_undeclared_shape(tmp_path: Path, text: str) -> None:
    _assert_invalid_profile(tmp_path, text)


def test_profile_contract_rejects_non_string_paths() -> None:
    with pytest.raises(TypeError, match="repository path must be a string"):
        RepositoryProfileDeclaration.model_validate(
            {
                "profile_id": "sample",
                "openspec": {"material_paths": ["openspec/**"]},
                "roots": {"docs": 1},
            }
        )


def test_profile_contract_rejects_complete_former_envelope(tmp_path: Path) -> None:
    _assert_invalid_profile(
        tmp_path,
        "schema_version = 1\n"
        'profile_id = "sample"\n'
        'profile_version = "1"\n'
        'ethos_contract_version = "1"\n\n'
        "[repository]\n"
        'kind = "documentation"\n'
        'root_subject = "sample"\n\n'
        "[openspec]\n"
        'material_paths = ["openspec/**"]\n',
    )


def test_current_profile_rejects_root_rules_workaround(tmp_path: Path) -> None:
    _assert_invalid_profile(
        tmp_path,
        'profile_id = "sample"\n\n'
        "[roots]\n"
        'rules = "."\n\n'
        "[openspec]\n"
        'material_paths = ["openspec/**"]\n',
    )


def test_profile_includes_declared_normative_sources_without_root_escape(tmp_path: Path) -> None:
    _write_profile(tmp_path, 'profile_id = "sample"\n\nnormative_sources = ["guidelines.md"]\n')

    profile = load_repository_profile(tmp_path)
    assert profile.declaration is not None
    assert profile.declaration.normative_sources == ("guidelines.md",)
    assert profile_root(tmp_path, "docs") == tmp_path / "docs"


def test_profile_loader_rejects_unreadable_profile(tmp_path: Path, monkeypatch) -> None:
    profile = _write_profile(tmp_path, "profile_id = 'sample'\n")
    original = Path.read_text

    def unreadable(path: Path, *args, **kwargs) -> str:
        if path == profile.resolve():
            raise OSError
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable)

    assert load_repository_profile(tmp_path).state == "invalid"


def test_invalid_profile_never_falls_back_to_default_roots(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "profile_id = 'sample'\n[roots]\ndocs = '../docs'\n",
    )

    loaded = load_repository_profile(tmp_path)

    assert loaded.state == "invalid"
    with pytest.raises(ValueError, match="repository_profile_invalid"):
        profile_root(tmp_path, "docs")


def test_profile_loader_never_falls_back_from_an_invalid_tree_ref(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    _write_profile(tmp_path, "profile_id = 'working-tree'\n")

    with pytest.raises(ValueError, match="repository_tree_ref_invalid"):
        load_committed_repository_profile(tmp_path, "deadbeef" * 5)
