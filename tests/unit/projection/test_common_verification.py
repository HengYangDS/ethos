"""Qualify installed common verification semantics with real native CUE outputs."""

import pytest
import tomli_w
import yaml

from ethos.adapters.projections.cue import compile_projections
from ethos.repository.policy.projections import projection_relations

DECLARATION = ".config/checks/ci-projection/policy.toml"
MODEL = ".config/ci/pipeline.cue"


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
