"""Exercise typed native compiler inputs without a second source authority."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest
import tomli_w
import yaml

from ethos.adapters.gates.provenance.observation import integrity_report
from ethos.adapters.mutation import carrier_edit
from ethos.adapters.mutation import projection
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


def test_product_common_model_has_real_repository_instance_and_native_inputs(tmp_path):
    """An adopter compiles the common model without its own compiler or ETHOS checkout."""
    configuration = {
        "schema": "ethos-ci-template-consistency-v1",
        "compiler": {
            "source": MODEL,
            "common": ".config/ci/verification.cue",
            "inputs": {"ci": ".config/checks/ci-projection/parameters.toml"},
        },
        "projection": [
            {"kind": "cue", "provider": "github", "projection": ".github/workflows/ci.yml"},
            {"kind": "cue", "provider": "gitlab", "projection": ".gitlab-ci.yml"},
        ],
    }
    parameters = {
        "name": "Documentation verification",
        "accepted_branch": "dev",
        "release_branch": "main",
        "report_path": "build/evidence/ci/verification.json",
        "timeout_minutes": 15,
        "github": {"runners": ["ubuntu-latest", "macos-latest", "windows-latest"]},
        "gitlab": {
            "runners": {
                "linux": {
                    "system": "linux",
                    "review_tags": ["reviewed"],
                    "protected_tags": ["protected"],
                    "image": "registry.invalid/supply@sha256:" + "a" * 64,
                }
            }
        },
        "supply": {"mise_version": "2026.10.14"},
    }
    files = {
        DECLARATION: tomli_w.dumps(configuration),
        MODEL: (
            "package ci\n"
            "compiled: providers: (#Verification & {parameters: _inputs.ci}).providers\n"
            'compiled: providers: github: jobs: business: {"runs-on": "ubuntu-latest", '
            'steps: [{run: "echo business"}]}\n'
            'compiled: providers: gitlab: business: {stage: "verify", script: ["echo business"]}\n'
        ),
        ".config/checks/ci-projection/parameters.toml": tomli_w.dumps(parameters),
    }
    original_paths = tuple(tmp_path.iterdir())
    relations = projection_relations(files)
    assert all(
        relation.inputs == (".config/checks/ci-projection/parameters.toml",)
        for relation in relations
    )
    assert all(".config/ci/verification.cue" not in relation.materials for relation in relations)
    rendered = compile_projections(tmp_path, DECLARATION, files)
    github, gitlab = (yaml.safe_load(rendered[provider]) for provider in ("github", "gitlab"))
    assert github["jobs"]["verify"]["strategy"]["matrix"]["os"] == parameters["github"]["runners"]
    assert gitlab["verify:linux:review"]["tags"] == ["reviewed"]
    assert github["jobs"]["business"]["steps"] == [{"run": "echo business"}]
    assert gitlab["business"]["script"] == ["echo business"]
    assert github["jobs"]["verify"]["steps"][-1]["with"]["path"] == parameters["report_path"]
    assert gitlab["verify:linux:review"]["script"] == [
        (
            "mise exec --locked -- ethos prove --host --execute --full --json "
            "> build/evidence/ci/verification.json"
        )
    ]
    assert compile_projections(tmp_path, DECLARATION, files, observations=rendered) == rendered
    drift = {
        **rendered,
        "github": rendered["github"].replace("Documentation verification", "Forged name"),
    }
    with pytest.raises(ValueError, match="cue_projection_drift"):
        compile_projections(tmp_path, DECLARATION, files, observations=drift)
    assert tuple(tmp_path.iterdir()) == original_paths


def test_product_common_binding_cannot_be_replaced_by_repository_output(tmp_path):
    """Declaring a shared model requires the actual output to retain its common contract."""
    files = _materials("package.toml")
    configuration = tomllib.loads(files[DECLARATION])
    configuration["compiler"] = {
        "source": MODEL,
        "common": ".config/ci/verification.cue",
        "inputs": {"ci": "policy.toml"},
    }
    files[DECLARATION] = tomli_w.dumps(configuration)
    files["policy.toml"] = tomli_w.dumps(
        {
            "name": "Documentation verification",
            "accepted_branch": "dev",
            "release_branch": "main",
            "timeout_minutes": 15,
            "supply": {"mise_version": "2026.10.14"},
            "github": {"runners": ["ubuntu-latest"]},
            "gitlab": {
                "runners": {
                    "linux": {
                        "system": "linux",
                        "review_tags": ["reviewed"],
                        "protected_tags": ["protected"],
                    }
                }
            },
        }
    )
    files[MODEL] = "package ci\ncompiled: parameters: _inputs.ci\n"
    rendered = compile_projections(tmp_path, DECLARATION, files)
    assert yaml.safe_load(rendered["github"])["name"] == "Documentation verification"
    duplicate = tomllib.loads(files[DECLARATION])
    duplicate["projection"].append(
        {
            "kind": "cue",
            "provider": "github",
            "projection": ".github/workflows/duplicate.yml",
        }
    )
    with pytest.raises(ValueError, match="projection_provider_conflict"):
        projection_relations({**files, DECLARATION: tomli_w.dumps(duplicate)})
    files[MODEL] = 'package ci\ncompiled: providers: github: name: "Replaced"\n'
    with pytest.raises(ValueError, match="cue_compilation_failed"):
        compile_projections(tmp_path, DECLARATION, files)


def test_product_common_verification_binds_source_supply_and_trust_partitions(tmp_path):
    """Real provider output binds supply, review trust, release inputs and bounded execution."""
    configuration = {
        "schema": "ethos-ci-template-consistency-v1",
        "compiler": {
            "source": MODEL,
            "common": ".config/ci/verification.cue",
            "inputs": {"ci": "parameters.toml"},
        },
        "projection": [
            {"kind": "cue", "provider": "github", "projection": ".github/workflows/ci.yml"},
            {"kind": "cue", "provider": "gitlab", "projection": ".gitlab-ci.yml"},
        ],
    }
    parameters = {
        "name": "Documentation verification",
        "accepted_branch": "dev",
        "release_branch": "main",
        "report_path": "build/evidence/ci/verification.json",
        "timeout_minutes": 20,
        "github": {"runners": ["ubuntu-latest", "macos-latest", "windows-latest"]},
        "gitlab": {
            "runners": {
                "linux": {
                    "system": "linux",
                    "review_tags": ["container-review"],
                    "protected_tags": ["container-protected"],
                    "image": "registry.invalid/supply@sha256:" + "a" * 64,
                },
                "windows": {
                    "system": "windows",
                    "review_tags": ["windows-review"],
                    "protected_tags": ["windows-protected"],
                    "resource_group": "windows-verification",
                },
            },
        },
        "supply": {"mise_version": "2026.10.14"},
    }
    files = {
        DECLARATION: tomli_w.dumps(configuration),
        MODEL: "package ci\ncompiled: parameters: _inputs.ci\n",
        "parameters.toml": tomli_w.dumps(parameters),
    }
    providers = compile_projections(tmp_path, DECLARATION, files)
    github, gitlab = (yaml.safe_load(providers[key]) for key in ("github", "gitlab"))
    github_jobs = github["jobs"]
    assert "proposal/**" in github["on"]["push"]["branches"]
    assert github["on"]["pull_request"]["branches"] == ["dev", "main"]
    assert "release" not in github["on"]
    assert github["on"]["workflow_dispatch"] == {}
    assert "offline" not in github_jobs
    cold_steps = github_jobs["verify"]["steps"]
    assert cold_steps[1]["uses"].startswith("jdx/mise-action@")
    assert cold_steps[1]["with"] == {
        "version": "2026.10.14",
        "install": False,
        "cache": False,
    }
    assert cold_steps[2]["run"] == "mise install --locked --jobs=1"
    assert "npm" not in str(cold_steps)
    assert {key for key in gitlab if not key.startswith(".") and isinstance(gitlab[key], dict)} >= {
        "verify:linux:review",
        "verify:linux:protected",
        "verify:windows:review",
        "verify:windows:protected",
    }
    review, protected = (gitlab[f"verify:windows:{kind}"] for kind in ("review", "protected"))
    assert review["tags"] == ["windows-review"]
    assert protected["tags"] == ["windows-protected"]
    assert review["resource_group"] == protected["resource_group"] == "windows-verification"
    assert "CI_COMMIT_REF_PROTECTED" in str(protected["rules"])
    assert "merge_request_event" in str(review["rules"])
    assert not any(key.startswith("offline:") for key in gitlab)
    assert gitlab["verify:linux:protected"]["image"].endswith("a" * 64)
    assert compile_projections(tmp_path, DECLARATION, files, observations=providers) == providers


def test_native_projection_preview_check_and_patch_share_complete_group(tmp_path, monkeypatch):
    """The installed command's owner prepares all outputs and applies only an exact native patch."""
    root = init_git_repo(tmp_path / "repository")
    files = _materials("package.toml")
    executable = locked_tool(ROOT, "cue")
    files[MODEL] = run_command(
        tmp_path, (str(executable), "fmt", "-"), stdin=files[MODEL], timeout=15, check=True
    ).stdout
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    commit_fixture(root, "bind exact projection inputs")
    snapshot = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    preview = projection.project_repository(root)
    assert preview["verdict"] == "pass"
    assert not preview["applied"]
    assert {edit["path"] for edit in preview["edits"]} == {
        ".github/workflows/ci.yml",
        ".gitlab-ci.yml",
    }
    assert preview["patch"]
    assert {path: path.read_bytes() for path in snapshot} == snapshot
    rejected = projection.project_repository(root, check=True)
    assert rejected["verdict"] == "block"
    assert rejected["required_gaps"] == [
        "generated_projection_drift:.github/workflows/ci.yml",
        "generated_projection_drift:.gitlab-ci.yml",
    ]
    monkeypatch.setattr(carrier_edit, "prewrite_guard", lambda **_kwargs: {"verdict": "pass"})
    monkeypatch.setattr(carrier_edit, "_authority_gaps", lambda *_args: [])
    applied = projection.project_repository(
        root,
        apply=True,
        authorize=True,
        expect_head=preview["head"],
        preview_patch=preview["patch"],
    )
    assert applied["verdict"] == "pass", applied
    assert applied["applied"]
    assert all(applied["preservation"].values())
    assert projection.project_repository(root, check=True)["verdict"] == "pass"
    (root / "policy.toml").write_text('title = "Changed input"\n', encoding="utf-8")
    stale = projection.project_repository(
        root,
        apply=True,
        authorize=True,
        expect_head=preview["head"],
        preview_patch=preview["patch"],
    )
    assert stale["verdict"] == "block"
    assert stale["required_gaps"] == ["carrier_edit_preview_patch_mismatch"]


def test_native_projection_refuses_relation_change_during_compilation(tmp_path, monkeypatch):
    """A declaration edited after capture cannot redirect the original patch's target."""
    root = init_git_repo(tmp_path / "repository")
    files = _materials("package.toml")
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    commit_fixture(root, "bind exact projection inputs")
    original = projection.render_projections

    def changed_relation(*args, **kwargs):
        result = original(*args, **kwargs)
        declaration = tomllib.loads(files[DECLARATION])
        declaration["projection"][0]["projection"] = ".github/workflows/replaced.yml"
        (root / DECLARATION).write_text(tomli_w.dumps(declaration), encoding="utf-8")
        return result

    monkeypatch.setattr(projection, "render_projections", changed_relation)
    report = projection.project_repository(root)
    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["projection_input_changed"]
    assert not (root / ".github/workflows/ci.yml").exists()
    assert not (root / ".github/workflows/replaced.yml").exists()


@pytest.mark.parametrize("supply", ["invalid", "", [], 3, {}, {"config": "config.toml"}])
def test_common_projection_refuses_explicit_invalid_supply_without_effects(tmp_path, supply):
    """Product supply is selected by omission, not by an invalid repository declaration."""
    root = init_git_repo(tmp_path / "repository")
    files = _materials("package.toml")
    configuration = tomllib.loads(files[DECLARATION])
    configuration["compiler"].update(common=".config/ci/verification.cue", supply=supply)
    declaration = root / DECLARATION
    declaration.parent.mkdir(parents=True)
    declaration.write_text(tomli_w.dumps(configuration), encoding="utf-8")
    commit_fixture(root, "bind invalid explicit compiler supply")
    before = declaration.read_bytes()
    result = projection.project_repository(root)
    assert result["verdict"] == "block"
    assert result["applied"] is False
    assert result["required_gaps"] == [
        f"projection_{'path' if isinstance(supply, dict) else 'compiler'}_invalid:{DECLARATION}"
    ]
    assert declaration.read_bytes() == before
    assert not (root / ".github/workflows/ci.yml").exists()
    assert not (root / ".gitlab-ci.yml").exists()
