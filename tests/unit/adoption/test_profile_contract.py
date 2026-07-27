from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import profile_evidence_roots
from ethos.repository.profile import profile_root
from ethos.repository.profile import render_repository_profile


def test_profile_contract_is_strict_frozen_and_deterministic(tmp_path: Path) -> None:
    declaration = RepositoryProfileDeclaration.bootstrap('sample<repo&"')

    rendered = render_repository_profile(declaration)

    assert rendered == (
        'profile_id = "sample<repo&\\""\n'
        "\n"
        "[openspec]\n"
        "material_paths = [\n"
        '    ".ethos/profile.toml",\n'
        '    "openspec/**",\n'
        '    "docs/governance/**",\n'
        '    "rules/**",\n'
        "]\n"
    )
    with pytest.raises(ValidationError):
        declaration.profile_id = "mutable"
    with pytest.raises(TypeError):
        declaration.proof.code_correctness_map["behavior"] = "mutable"
    with pytest.raises(ValidationError):
        RepositoryProfileDeclaration.model_validate(
            {
                "profile_id": "sample",
                "openspec": {"material_paths": ["openspec/**"]},
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
    assert loaded.declaration.openspec.material_paths == (
        ".ethos/profile.toml",
        "openspec/**",
        "docs/governance/**",
        "rules/**",
    )


@pytest.mark.parametrize(
    "text",
    [
        "profile_id = 'sample'\n",
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
            "[roots]\nlocal_state = '.'\n"
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
        'profile_id = "sample"\n\n'
        'normative_sources = ["guidelines.md"]\n\n'
        "[openspec]\n"
        'material_paths = ["openspec/**"]\n',
        encoding="utf-8",
    )

    assert profile_evidence_roots(tmp_path) == (
        ".ethos/profile.toml",
        "rules",
        "guidelines.md",
        "openspec",
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
        "profile_id = 'sample'\n[openspec]\nmaterial_paths = ['openspec/**']\n"
        "[roots]\ndurable_evidence = '../evidence'\n",
        encoding="utf-8",
    )

    loaded = load_repository_profile(tmp_path)

    assert loaded.state == "invalid"
    with pytest.raises(ValueError, match="adopter_profile_invalid"):
        profile_root(tmp_path, "durable_evidence")
