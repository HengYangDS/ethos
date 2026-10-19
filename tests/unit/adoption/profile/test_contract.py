"""Immutable profile declarations retain native proof roots and reject invalid selection."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.profile import load_committed_repository_profile
from ethos.repository.adoption.fleet import inspect_adopter
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import profile_root
from ethos.repository.profile import render_repository_profile
from tests.support.governed_repository import git
from tests.support.literal_cases import literal_case

RELOCATED_OPENSPEC_PROFILE = 'profile_id = "sample"\n\n[roots]\nopenspec = "contracts"\n'
RETIRED_PROFILES = {
    "registry-projection": 'profile_id = "sample"\n\n[proof]\ncode_correctness_gates = ["tests"]\n'
    '\n[[proof.gates]]\nid = "tests"\nkind = "test"\n'
    'command = ["pytest"]\nregistries = ["quality"]\n',
    "former-envelope": 'schema_version = 1\nprofile_id = "sample"\nprofile_version = "1"\n'
    'ethos_contract_version = "1"\n\n[repository]\nkind = "documentation"\n'
    'root_subject = "sample"\n\n[openspec]\nmaterial_paths = ["openspec/**"]\n',
    "root-rules-workaround": 'profile_id = "sample"\n\n[roots]\nrules = "."\n\n'
    '[openspec]\nmaterial_paths = ["openspec/**"]\n',
    "openspec-relocation": RELOCATED_OPENSPEC_PROFILE,
}


def _write_profile(root: Path, text: str) -> Path:
    profile = root / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(text, encoding="utf-8")
    return profile


def _validate_metadata_binding(field: str, file_name: str, authority_ref: str) -> None:
    """Validate one OpenSpec metadata binding through the immutable profile declaration."""
    binding = {"file_name": file_name, "authority_ref": authority_ref}
    RepositoryProfileDeclaration.model_validate(
        {"profile_id": "sample", "openspec": {"material_paths": ["**"], field: [binding]}}
    )


@pytest.mark.parametrize(
    "file_name",
    [
        "spec.md",
        "../capability.toml",
        "code.py",
        "nested/data.json",
        "",
        "nested\\data.json",
        "bad\nname.toml",
        "bad\x00name.toml",
        "*.json",
    ],
)
@pytest.mark.parametrize("field", ["capability_metadata", "specs_root_metadata"])
def test_profile_rejects_unsafe_capability_metadata_bindings(file_name: str, field: str) -> None:
    """Metadata is an exact native data member, never a new normative or executable carrier."""
    with pytest.raises(ValidationError):
        _validate_metadata_binding(field, file_name, "rules/native-contract.md")


@pytest.mark.parametrize(
    "authority_ref", ["/outside.md", "../outside.md", "nested/../owner.md", "owner\n.md"]
)
@pytest.mark.parametrize("field", ["capability_metadata", "specs_root_metadata"])
def test_metadata_authority_requires_an_exact_repository_path(
    authority_ref: str, field: str
) -> None:
    """A metadata owner is an exact contained file path, not an external or ambiguous locator."""
    with pytest.raises(ValidationError):
        _validate_metadata_binding(field, "data.json", authority_ref)


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
        RepositoryProfileDeclaration.model_validate({"profile_id": "sample", "extra": True})

    _write_profile(tmp_path, rendered)
    loaded = load_repository_profile(tmp_path)

    assert loaded.state == "valid"
    assert loaded.declaration is not None
    assert loaded.declaration.profile_id == 'sample<repo&"'
    assert loaded.declaration.openspec is None


@pytest.mark.parametrize(
    "fields",
    [{"roots": {"durable_evidence": "evidence"}}, {"evidence": {"durable_roots": ["evidence"]}}],
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
    """Retain native proof declarations and the same applicable shared floor in both views."""
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "test")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    _write_profile(
        tmp_path,
        render_repository_profile(
            RepositoryProfileDeclaration.model_validate(
                {"profile_id": "native-check-adopter", "proof": _dependency_proof()}
            )
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
    assert worktree.gate_ids == committed.gate_ids
    proof = worktree.profile.declaration.proof
    assert proof.code_correctness_gates == ("checks", "static")
    gates = set(worktree.gate_ids)
    assert gates == {"checks", "static", "behavior"}
    assert worktree.declaration.proof_sets == committed.declaration.proof_sets
    assert worktree.declaration.proof_sets.default == ("checks", "static")
    assert worktree.declaration.proof_sets.full == ("checks", "static")
    assert worktree.gate_ids.index("behavior") < worktree.gate_ids.index("checks")
    assert worktree.registry["behavior"].command == ()
    assert worktree.registry["behavior"].execution_mode == "provider"
    assert proof.code_correctness_map == {"behavior": "behavior", "static-analysis": "static"}
    assert "optional" in worktree.registry
    assert "optional" not in worktree.gate_ids
    assert [gate.id for gate in worktree.declaration.proof_gates(("optional",))] == ["optional"]


def _dependency_proof() -> dict[str, object]:
    """Keep default roots distinct from their complete native execution closure."""
    return {
        "code_correctness_gates": ["checks", "static"],
        "code_correctness_map": {"behavior": "behavior", "static-analysis": "static"},
        "gates": [
            {
                "id": "checks",
                "kind": "test",
                "command": ["sample", "check"],
                "depends_on": ["behavior"],
            },
            {"id": "static", "kind": "lint", "command": ["sample", "format"]},
            {
                "id": "behavior",
                "kind": "test",
                "providers": ["ethos.adapters.gates.code_quality:behavior_report"],
            },
            {"id": "optional", "kind": "lint", "command": ["sample", "optional"]},
        ],
    }


def test_profile_native_document_roots_do_not_require_code_axes() -> None:
    """Document gates have a complete native closure without fictional code evidence."""
    declaration = RepositoryProfileDeclaration.model_validate(
        {
            "profile_id": "document-only",
            "proof": {
                "code_correctness_gates": ["docs-registry", "markdown-links"],
                "gates": [
                    {
                        "id": "docs-registry",
                        "kind": "docs",
                        "providers": ["ethos.surface.cli.root.reference:docs_registry_report"],
                    },
                    {
                        "id": "markdown-links",
                        "kind": "docs",
                        "providers": ["ethos.adapters.gates.tool:markdown_links_report"],
                    },
                ],
            },
        }
    )

    assert declaration.proof.code_correctness_gates == ("docs-registry", "markdown-links")
    assert dict(declaration.proof.code_correctness_map) == {}


@pytest.mark.parametrize(
    "fault", ["missing", "disconnected-axis", "cycle", "duplicate", "malformed", "unmapped"]
)
def test_profile_rejects_incomplete_native_dependency_closure(fault: str) -> None:
    """A profile cannot omit, detach, cycle or misattribute its required observations."""
    proof = _dependency_proof()
    gates = proof["gates"]
    if fault == "missing":
        gates.pop(2)
    elif fault == "disconnected-axis":
        gates[0].pop("depends_on")
    elif fault == "cycle":
        gates[2]["depends_on"] = ["checks"]
    elif fault == "duplicate":
        gates.append(gates[2].copy())
    elif fault == "malformed":
        gates[2]["command"] = ["sample", "test"]
    else:
        proof["code_correctness_map"]["behavior"] = "undeclared"
    with pytest.raises(ValidationError):
        RepositoryProfileDeclaration.model_validate({"profile_id": "sample", "proof": proof})


@pytest.mark.parametrize("text", RETIRED_PROFILES.values(), ids=list(RETIRED_PROFILES))
def test_profile_rejects_retired_shapes_and_root_workarounds(tmp_path: Path, text: str) -> None:
    """Retired fields, the former envelope and renamed native roots such as OpenSpec never load."""
    _assert_invalid_profile(tmp_path, text)


@pytest.mark.parametrize(
    "text",
    literal_case(
        "adoption.test_profile_contract:parametrize:test_profile_contract_rejects_incomplete_or_undeclared_shape:1"
    ),
)
def test_profile_contract_rejects_incomplete_or_undeclared_shape(tmp_path: Path, text: str) -> None:
    _assert_invalid_profile(tmp_path, text)


def test_profile_contract_rejects_non_string_paths() -> None:
    with pytest.raises(ValidationError, match="valid string"):
        RepositoryProfileDeclaration.model_validate(
            {
                "profile_id": "sample",
                "openspec": {"material_paths": ["openspec/**"]},
                "roots": {"docs": 1},
            }
        )


def test_adopter_inspection_does_not_accept_a_relocated_open_spec_root(tmp_path: Path) -> None:
    """Capability discovery must agree with the native OpenSpec reader."""
    relocated = tmp_path / "contracts"
    (relocated / "specs").mkdir(parents=True)
    (relocated / "config.yaml").write_text("schema: spec-driven\n", encoding="utf-8")
    _write_profile(tmp_path, RELOCATED_OPENSPEC_PROFILE)

    report = inspect_adopter(tmp_path)

    assert report["verdict"] == "block"
    assert report["adopter"]["capabilities"]["openspec"] is False


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
    _write_profile(tmp_path, "profile_id = 'sample'\n[roots]\ndocs = '../docs'\n")

    loaded = load_repository_profile(tmp_path)

    assert loaded.state == "invalid"
    with pytest.raises(ValueError, match="repository_profile_invalid"):
        profile_root(tmp_path, "docs")


def test_profile_loader_never_falls_back_from_an_invalid_tree_ref(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    _write_profile(tmp_path, "profile_id = 'working-tree'\n")

    with pytest.raises(ValueError, match="repository_tree_ref_invalid"):
        load_committed_repository_profile(tmp_path, "deadbeef" * 5)
