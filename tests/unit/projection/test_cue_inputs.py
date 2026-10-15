"""Exercise typed native compiler inputs without a second source authority."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest
import tomli_w
import yaml

from ethos.adapters.gates.provenance.observation import integrity_report
from ethos.adapters.process import run_command
from ethos.adapters.projections.compiler import render_projections
from ethos.adapters.projections.cue import compile_projections
from ethos.adapters.toolchain.mise import locked_tool
from ethos.repository.policy.projections import projection_relations
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo
from tools.ci.ci_projection import compile_providers

ROOT = Path(__file__).resolve().parents[3]
DECLARATION = ".config/checks/ci-projection/policy.toml"
MODEL = ".config/ci/pipeline.cue"
SUPPLY = {"config": ".config/mise/config.toml", "lock": ".config/mise/mise.lock"}
PACKAGE = {"engines": {"node": "26.x"}, "private": True, "optional": None, "values": [1, 2.5]}
MODEL_SOURCE = """_inputs: _
compiled: providers: {
    github: {name: _inputs.policy.title, package: _inputs.package}
    gitlab: {name: _inputs.policy.title, package: _inputs.package}
}
"""


def _materials(package_reference: str | dict) -> dict[str, str]:
    """Keep the real package JSON and native supply in their existing carriers."""
    configuration = {
        "schema": "ethos-ci-template-consistency-v1",
        "compiler": {
            "source": MODEL,
            "supply": SUPPLY,
            "inputs": {"policy": "policy.toml", "package": package_reference},
        },
        "projection": [
            {"kind": "cue", "provider": "github", "projection": ".github/workflows/ci.yml"},
            {"kind": "cue", "provider": "gitlab", "projection": ".gitlab-ci.yml"},
        ],
    }
    return {
        DECLARATION: tomli_w.dumps(configuration),
        MODEL: MODEL_SOURCE,
        "policy.toml": 'title = "Documentation verification"\n',
        "package.json": json.dumps(PACKAGE),
        "package.toml": tomli_w.dumps({"engines": {"node": "26.x"}, "private": True}),
        **{relative: (ROOT / relative).read_text(encoding="utf-8") for relative in SUPPLY.values()},
    }


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        ("package.toml", {"engines": {"node": "26.x"}, "private": True}),
        (
            {"path": "package.toml", "format": "toml"},
            {"engines": {"node": "26.x"}, "private": True},
        ),
        ({"path": "package.json", "format": "json"}, PACKAGE),
    ],
)
def test_native_input_formats_preserve_data_and_complete_outputs(tmp_path, reference, expected):
    """Native JSON types and existing TOML meanings reach every declared provider."""
    files = _materials(reference)
    before = dict(files)
    original_paths = tuple(tmp_path.iterdir())
    rendered = compile_projections(tmp_path, DECLARATION, files)
    assert set(rendered) == {"github", "gitlab"}
    assert {provider: yaml.safe_load(content) for provider, content in rendered.items()} == {
        provider: {"name": "Documentation verification", "package": expected}
        for provider in ("github", "gitlab")
    }
    assert compile_projections(tmp_path, DECLARATION, files, observations=rendered) == rendered
    assert files == before
    assert tuple(tmp_path.iterdir()) == original_paths


def test_typed_input_dependency_closure_rebuilds_the_complete_native_group(tmp_path):
    """One JSON change selects both existing outputs rather than a copied manifest."""
    files = _materials({"path": "package.json", "format": "json"})
    original_paths = tuple(tmp_path.iterdir())
    relations = projection_relations(files)
    expected = ("policy.toml", "package.json", *SUPPLY.values())
    assert len(relations) == 2
    assert all(relation.inputs == expected for relation in relations)
    baseline = render_projections(
        tmp_path, relations, files, {"package.json": files["package.json"]}
    )
    changed = {**files, "package.json": json.dumps({**PACKAGE, "private": False})}
    updated = render_projections(
        tmp_path, relations, changed, {"package.json": changed["package.json"]}
    )
    assert set(updated) == {relation.output for relation in relations}
    assert updated != baseline
    assert all(
        yaml.safe_load(content)["package"]["private"] is False for content in updated.values()
    )
    assert tuple(tmp_path.iterdir()) == original_paths


@pytest.mark.parametrize(
    "reference",
    [
        {"path": "package.json", "format": "yaml"},
        {"path": "package.json", "format": ["json"]},
        {"path": "package.json"},
        {"path": "package.json", "format": "json", "fallback": "package.toml"},
        {"path": "../package.json", "format": "json"},
        {"path": 5, "format": "json"},
        ["package.json", "json"],
    ],
)
def test_invalid_typed_input_refs_fail_without_effects(tmp_path, reference):
    """Invalid declarations cannot change native source selection or acquire fallback."""
    files = _materials(reference)
    before = dict(files)
    original_paths = tuple(tmp_path.iterdir())
    with pytest.raises(ValueError, match=r"projection_(?:compiler|input|path)"):
        projection_relations(files)
    with pytest.raises(ValueError, match=r"projection_(?:compiler|input|path)"):
        compile_projections(tmp_path, DECLARATION, files)
    assert files == before
    assert tuple(tmp_path.iterdir()) == original_paths


@pytest.mark.parametrize(
    ("reference", "path", "content", "error"),
    [
        ({"path": "package.json", "format": "json"}, "package.json", "{", json.JSONDecodeError),
        ({"path": "package.toml", "format": "toml"}, "package.toml", "[", ValueError),
        ({"path": "package.json", "format": "json"}, "package.json", None, KeyError),
        ({"path": "package.toml", "format": "toml"}, "package.toml", None, KeyError),
    ],
)
def test_native_parse_and_missing_input_errors_preserve_source(
    tmp_path, reference, path, content, error
):
    """Missing files and malformed carriers retain their native diagnostic type."""
    files = _materials(reference)
    if content is None:
        files.pop(path)
    else:
        files[path] = content
    before = dict(files)
    original_paths = tuple(tmp_path.iterdir())
    with pytest.raises(error):
        compile_projections(tmp_path, DECLARATION, files)
    assert files == before
    assert tuple(tmp_path.iterdir()) == original_paths


def test_typed_inputs_reject_observed_drift_and_incomplete_provider_output(tmp_path):
    """Caller observations never enter CUE or qualify a missing group member."""
    files = _materials({"path": "package.json", "format": "json"})
    before = dict(files)
    original_paths = tuple(tmp_path.iterdir())
    rendered = compile_projections(tmp_path, DECLARATION, files)
    observed = {**rendered, "github": rendered["github"].replace("26.x", "22.x")}
    with pytest.raises(ValueError, match="cue_projection_drift"):
        compile_projections(tmp_path, DECLARATION, files, observations=observed)
    with pytest.raises(ValueError, match="cue_projection_drift"):
        compile_projections(
            tmp_path, DECLARATION, files, observations={"github": rendered["github"]}
        )
    partial = {**files, MODEL: '_inputs: _\ncompiled: providers: github: {name: "incomplete"}\n'}
    with pytest.raises(ValueError, match="cue_projection_providers_mismatch"):
        compile_projections(tmp_path, DECLARATION, partial)
    assert files == before
    assert tuple(tmp_path.iterdir()) == original_paths


def test_relocation_and_ambient_policy_cannot_replace_declared_materials(tmp_path, monkeypatch):
    """Only the supplied source and locked native tool survive a root change."""
    files = _materials({"path": "package.json", "format": "json"})
    source = tmp_path / "original"
    relocated = tmp_path / "relocated"
    for root in (source, relocated):
        root.mkdir()
        (root / "ambient.cue").write_text('compiled: providers: github: {name: "forged"}\n')
        (root / "package.json").write_text('{"engines":{"node":"22.x"}}\n')
    ambient = tmp_path / "ambient.toml"
    ambient.write_text('[tools]\ncue = "0.1.0"\n[hooks]\nenter = "touch FORBIDDEN"\n')
    monkeypatch.setenv("MISE_GLOBAL_CONFIG_FILE", str(ambient))
    monkeypatch.setenv("CUE_REGISTRY", "example.invalid")
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    expected = compile_projections(source, DECLARATION, files)
    assert compile_projections(relocated, DECLARATION, files) == expected
    assert {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before


@pytest.mark.parametrize("fault", ["missing-lock", "version-mismatch"])
def test_typed_inputs_keep_locked_supply_admission(tmp_path, fault):
    """A PATH tool cannot silently repair missing locks or a wrong declared version."""
    files = _materials({"path": "package.json", "format": "json"})
    if fault == "missing-lock":
        files.pop(SUPPLY["lock"])
        error, diagnostic, executable = KeyError, "mise.lock", None
    else:
        executable = locked_tool(ROOT, "cue")
        configuration = tomllib.loads(files[SUPPLY["config"]])
        locked_version = configuration["tools"]["cue"]
        different_version = "0.0.0" if locked_version != "0.0.0" else "0.0.1"
        configuration["tools"]["cue"] = different_version
        files[SUPPLY["config"]] = tomli_w.dumps(configuration)
        error, diagnostic = ValueError, "cue_version_mismatch"
    before = dict(files)
    original_paths = tuple(tmp_path.iterdir())
    with pytest.raises(error, match=diagnostic):
        compile_projections(tmp_path, DECLARATION, files, executable=executable)
    assert files == before
    assert tuple(tmp_path.iterdir()) == original_paths


def test_public_template_input_selection_uses_the_same_typed_contract(tmp_path):
    """The existing native template consumer selects JSON without inventing a mirror."""
    files = _materials({"path": "package.json", "format": "json"})
    executable = locked_tool(ROOT, "cue")
    files[MODEL] = run_command(
        tmp_path, (str(executable), "fmt", "-"), stdin=files[MODEL], timeout=15, check=True
    ).stdout
    for relative, content in files.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    expected = compile_projections(tmp_path, DECLARATION, files)
    assert compile_providers(tmp_path, observations=expected) == expected
    assert {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before


def test_source_integrity_observes_every_typed_generated_member(tmp_path):
    """Native integrity requires the complete same-source group and rejects drift."""
    root = init_git_repo(tmp_path / "repository")
    files = _materials({"path": "package.json", "format": "json"})
    rendered = compile_projections(root, DECLARATION, files)
    configuration = {
        "profile_id": "native-input-example",
        "proof": {
            "source_contracts": [
                {
                    "kind": "generated",
                    "input_refs": [DECLARATION],
                    "members": {
                        relative: [DECLARATION, relative]
                        for relative in (".github/workflows/ci.yml", ".gitlab-ci.yml")
                    },
                    "integrity_gate": "integrity",
                }
            ],
        },
    }
    outputs = {".github/workflows/ci.yml": rendered["github"], ".gitlab-ci.yml": rendered["gitlab"]}
    for relative, content in {
        **files,
        **outputs,
        ".ethos/profile.toml": tomli_w.dumps(configuration),
    }.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    commit_fixture(root, "bind typed native inputs to the complete generated group")
    before = {
        path: path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }
    observed = integrity_report(root)
    assert observed["verdict"] == "pass", observed
    assert set(observed["source_integrity"]["members"]) == set(outputs)
    assert {
        path: path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.parts
    } == before
    (root / "package.json").write_text(json.dumps({**PACKAGE, "private": False}), encoding="utf-8")
    commit_fixture(root, "change native input without regenerating either provider")
    rejected = integrity_report(root)
    assert rejected["verdict"] == "unknown", rejected
    assert rejected["required_gaps"] == [f"source_integrity_unproven:{path}" for path in outputs]
    profile = root / ".ethos/profile.toml"
    del configuration["proof"]["source_contracts"][0]["members"][".gitlab-ci.yml"]
    profile.write_text(tomli_w.dumps(configuration), encoding="utf-8")
    commit_fixture(root, "omit one member from the declared generated group")
    assert integrity_report(root)["verdict"] == "unknown"
