"""Qualify installed common verification semantics with real native CUE outputs."""

import json

import pytest
import tomli_w
import yaml

from ethos.adapters.projections.cue import compile_projections
from ethos.repository.paradigm.orchestration import ci_steps
from ethos.repository.paradigm.orchestration import inline_shell
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
            {
                "kind": "cue",
                "provider": "github",
                "projection": ".github/workflows/ci.yml",
            },
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
            {
                "kind": "cue",
                "provider": "github",
                "projection": ".github/workflows/ci.yml",
            },
            {"kind": "cue", "provider": "gitlab", "projection": ".gitlab-ci.yml"},
        ],
    }
    parameters = {
        "name": "Documentation verification",
        "accepted_branch": "dev",
        "release_branch": "main",
        "report_path": "build/evidence/ci/verification.json",
        "timeout_minutes": 20,
        "github": {
            "runners": [
                "ubuntu-latest",
                "ubuntu-24.04-arm",
                "macos-latest",
                "windows-latest",
            ]
        },
        "gitlab": {
            "variables": {
                "MISE_CONFIG_DIR": "$CI_PROJECT_DIR/build/runtime/work/mise-config",
                "MISE_CEILING_PATHS": "$CI_PROJECT_DIR/..",
                "MISE_TRUSTED_CONFIG_PATHS": "$CI_PROJECT_DIR/.config/mise/config.toml",
                "MISE_YES": "1",
            },
            "runners": {
                "linux": {
                    "system": "linux",
                    "review_tags": ["ci-linux-arm64-container"],
                    "protected_tags": ["ci-linux-arm64-container-protected"],
                    "image": "public.ecr.aws/docker/library/node:26-trixie@sha256:"
                    "1b84b89ada025e3b14543cbb837ffaa1c1b5273b841c5b94dd1a8f9c1d8cf7fe",
                    "preparation": [
                        "mkdir -p build/runtime/work/mise-bootstrap",
                        (
                            "curl --fail --silent --show-error --connect-timeout 10 --max-time 60 "
                            '--header "JOB-TOKEN: $CI_JOB_TOKEN" '
                            "--output build/runtime/work/mise-bootstrap/install.sh "
                            '"$CI_API_V4_URL/projects/$CI_PROJECT_ID/packages/generic/'
                            'mise/2026.10.17/install.sh"'
                        ),
                        "sha256sum --check .config/mise/install.sha256",
                        (
                            "curl --fail --silent --show-error --connect-timeout 10 --max-time 90 "
                            '--header "JOB-TOKEN: $CI_JOB_TOKEN" '
                            "--output build/runtime/work/mise-bootstrap/"
                            "mise-v2026.10.17-linux-arm64.tar.gz "
                            '"$CI_API_V4_URL/projects/$CI_PROJECT_ID/packages/generic/'
                            "mise/2026.10.17/"
                            'mise-v2026.10.17-linux-arm64.tar.gz"'
                        ),
                        (
                            "timeout --signal=TERM --kill-after=5s 120s env "
                            "MISE_VERSION=2026.10.17 "
                            "MISE_INSTALL_PATH=/usr/local/bin/mise MISE_INSTALL_HELP=0 "
                            'MISE_INSTALL_EXT=tar.gz MISE_TARBALL_URL="file://$CI_PROJECT_DIR/'
                            "build/runtime/work/mise-bootstrap/"
                            'mise-v2026.10.17-linux-arm64.tar.gz" '
                            "sh build/runtime/work/mise-bootstrap/install.sh"
                        ),
                    ],
                },
                "macos": {
                    "system": "macos",
                    "review_tags": ["ci-macos-arm64-review"],
                    "protected_tags": ["ci-macos-arm64-shell"],
                },
                "windows": {
                    "system": "windows",
                    "review_tags": ["ci-windows-arm64-review"],
                    "protected_tags": ["ci-windows-arm64-shell"],
                    "resource_group": "windows-verification",
                    "preparation": [
                        (
                            "$env:PATH = $env:PATH + [IO.Path]::PathSeparator + "
                            "[Environment]::GetEnvironmentVariable('Path', 'Machine')"
                        )
                    ],
                },
            },
        },
        "supply": {
            "mise_version": "2026.10.17",
            "checks": {
                "github": [
                    "mise exec --locked -- npm ci --ignore-scripts",
                    "mise exec --locked -- node tools/ci/install-native.mjs osv-scanner --download",
                    "mise exec --locked -- node tools/docs/cli.mjs audit",
                ],
                "gitlab": [
                    "mise exec --locked -- npm ci --ignore-scripts",
                    (
                        "mise exec --locked -- node tools/ci/install-native.mjs "
                        "osv-scanner --gitlab-package"
                    ),
                    "mise exec --locked -- node tools/docs/cli.mjs audit",
                ],
            },
        },
        "evidence_paths": ["build/evidence/dependencies/"],
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
        "version": "2026.10.17",
        "install": False,
        "cache": False,
    }
    assert cold_steps[2]["run"] == "mise install --locked --jobs=1"
    assert [
        step["run"] for step in cold_steps if step.get("name") == "Check locked supply"
    ] == parameters["supply"]["checks"]["github"]
    assert cold_steps[-1]["with"]["path"].splitlines() == [
        parameters["report_path"],
        *parameters["evidence_paths"],
    ]
    assert {key for key in gitlab if not key.startswith(".") and isinstance(gitlab[key], dict)} >= {
        "verify:linux:review",
        "verify:linux:protected",
        "verify:windows:review",
        "verify:windows:protected",
    }
    review, protected = (gitlab[f"verify:windows:{kind}"] for kind in ("review", "protected"))
    assert review["tags"] == ["ci-windows-arm64-review"]
    assert protected["tags"] == ["ci-windows-arm64-shell"]
    assert review["resource_group"] == protected["resource_group"] == "windows-verification"
    assert "CI_COMMIT_REF_PROTECTED" in str(protected["rules"])
    assert "merge_request_event" in str(review["rules"])
    assert not any(key.startswith("offline:") for key in gitlab)
    windows_steps = [
        step
        for step in ci_steps("gitlab", ".gitlab-ci.yml", providers["gitlab"])
        if step.job.startswith("verify:windows:")
    ]
    assert windows_steps
    assert not [step for step in windows_steps if inline_shell(step.command)]
    assert (
        gitlab["verify:linux:protected"]["image"]
        == parameters["gitlab"]["runners"]["linux"]["image"]
    )
    for name, runner in parameters["gitlab"]["runners"].items():
        for trust in ("review", "protected"):
            job = gitlab[f"verify:{name}:{trust}"]
            preparation = runner.get("preparation", [])
            mkdir = (
                "New-Item -ItemType Directory -Force build/evidence/ci"
                if runner["system"] == "windows"
                else "mkdir -p build/evidence/ci"
            )
            assert job["before_script"] == [
                *preparation,
                "mise install --locked --jobs=1",
                *parameters["supply"]["checks"]["gitlab"],
                mkdir,
            ]
            assert job["variables"] == {
                "GIT_DEPTH": "0",
                **parameters["gitlab"]["variables"],
                **runner.get("variables", {}),
            }
            assert job["artifacts"] == {
                "when": "always",
                "paths": [parameters["report_path"], *parameters["evidence_paths"]],
            }
            assert job["timeout"] == "20 minutes"
            assert len(job["script"]) == 1
            assert "ethos prove --host --execute --full" in job["script"][0]
    assert compile_projections(tmp_path, DECLARATION, files, observations=providers) == providers


@pytest.mark.parametrize("candidate_variable", [None, "DDWG_OFFLINE_CANDIDATE"])
def test_product_common_verification_preserves_additive_offline_jobs(tmp_path, candidate_variable):
    """Offline composition keeps protected API/web admission and the adopter's jobs."""
    configuration = {
        "compiler": {
            "source": MODEL,
            "common": ".config/ci/verification.cue",
            "inputs": {"ci": "parameters.toml"},
        },
        "projection": [{"provider": "gitlab"}],
    }
    parameters = {
        "name": "Documentation verification",
        "accepted_branch": "dev",
        "release_branch": "main",
        "timeout_minutes": 20,
        "supply": {"mise_version": "2026.10.17"},
        "gitlab": {
            "runners": {
                "windows": {
                    "system": "windows",
                    "review_tags": ["ci-windows-arm64-review"],
                    "protected_tags": ["ci-windows-arm64-shell"],
                }
            }
        },
    }
    variable = candidate_variable or "ETHOS_OFFLINE_CANDIDATE"
    if candidate_variable:
        parameters["gitlab"]["offline_candidate_variable"] = candidate_variable
    candidate_rule = {
        "if": (
            f'${variable} && $CI_COMMIT_REF_PROTECTED == "true" && '
            '($CI_COMMIT_BRANCH == "dev" || $CI_COMMIT_BRANCH == "main") && '
            '($CI_PIPELINE_SOURCE == "api" || $CI_PIPELINE_SOURCE == "web")'
        )
    }
    exclusion_rule = {"if": f"${variable}", "when": "never"}
    offline_jobs = {
        ".offline:verify": {
            "stage": "verify",
            "timeout": "25m",
            "interruptible": True,
            "rules": [
                candidate_rule,
                exclusion_rule,
                {"if": '$CI_COMMIT_TAG =~ /^v[^\\/]*$/ && $CI_PIPELINE_SOURCE == "web"'},
                {"if": '$CI_COMMIT_TAG =~ /^v[^\\/]*$/ && $CI_PIPELINE_SOURCE == "api"'},
            ],
            "script": [
                "mise exec --locked -- node tools/ci/offline-bundle.mjs acquire-gitlab",
                "mise exec --locked -- node tools/ci/offline-bundle.mjs install",
                "mise exec --locked -- ethos prove --host --execute --full --json",
            ],
        },
        "offline:verify:linux": {
            "extends": ".offline:verify",
            "tags": ["ci-linux-arm64-container-protected"],
        },
        "offline:verify:macos": {
            "extends": ".offline:verify",
            "tags": ["ci-macos-arm64-shell"],
        },
        "offline:verify:windows": {
            "extends": ".offline:verify",
            "tags": ["ci-windows-arm64-shell"],
            "resource_group": "windows-verification",
        },
    }
    files = {
        DECLARATION: tomli_w.dumps(configuration),
        MODEL: (
            "package ci\ncompiled: parameters: _inputs.ci\n"
            "compiled: providers: gitlab: " + json.dumps(offline_jobs) + "\n"
        ),
        "parameters.toml": tomli_w.dumps(parameters),
    }
    rendered = compile_projections(tmp_path, DECLARATION, files)
    gitlab = yaml.safe_load(rendered["gitlab"])
    assert gitlab["workflow"]["rules"] == [
        candidate_rule,
        exclusion_rule,
        {"if": '$CI_PIPELINE_SOURCE == "merge_request_event"'},
        {
            "if": "$CI_COMMIT_BRANCH =~ /^proposal\\// && $CI_OPEN_MERGE_REQUESTS",
            "when": "never",
        },
        {
            "if": (
                '$CI_COMMIT_BRANCH == "dev" || $CI_COMMIT_BRANCH == "main" || '
                "$CI_COMMIT_BRANCH =~ /^proposal\\// || $CI_COMMIT_TAG =~ /^v[^\\/]*$/"
            )
        },
    ]
    for name, job in offline_jobs.items():
        assert gitlab[name] == job
    for trust in ("review", "protected"):
        assert gitlab[f"verify:windows:{trust}"]["rules"][0] == exclusion_rule
        assert gitlab[f"verify:windows:{trust}"]["timeout"] == "20 minutes"
    assert compile_projections(tmp_path, DECLARATION, files, observations=rendered) == rendered


@pytest.mark.parametrize(
    ("increment", "constraint"),
    [
        (
            {"parameters": {"gitlab": {"offline_candidate_variable": "DDWG; echo bypass"}}},
            "offline_candidate_variable",
        ),
        (
            {"parameters": {"gitlab": {"runners": {"windows": {"preparation": [""]}}}}},
            "preparation",
        ),
        (
            {"parameters": {"gitlab": {"runners": {"windows": {"variables": {"GIT_DEPTH": "1"}}}}}},
            "GIT_DEPTH",
        ),
        (
            {"parameters": {"evidence_paths": ["build/evidence/../secret"]}},
            "evidence_paths",
        ),
        (
            {"providers": {"gitlab": {"verify:windows:protected": {"script": ["echo bypass"]}}}},
            "script",
        ),
        (
            {"providers": {"github": {"jobs": {"verify": {"timeout-minutes": 121}}}}},
            "timeout-minutes",
        ),
    ],
)
def test_product_common_verification_refuses_lossy_composition(tmp_path, increment, constraint):
    """Typed increments cannot bypass proof, full history, evidence scope or execution bounds."""
    configuration = {
        "compiler": {
            "source": MODEL,
            "common": ".config/ci/verification.cue",
            "inputs": {"ci": "parameters.toml"},
        },
        "projection": [{"provider": provider} for provider in ("github", "gitlab")],
    }
    parameters = {
        "name": "Documentation verification",
        "accepted_branch": "dev",
        "release_branch": "main",
        "timeout_minutes": 20,
        "supply": {"mise_version": "2026.10.17"},
        "github": {"runners": ["windows-latest"]},
        "gitlab": {
            "runners": {
                "windows": {
                    "system": "windows",
                    "review_tags": ["review"],
                    "protected_tags": ["protected"],
                }
            }
        },
    }
    files = {
        DECLARATION: tomli_w.dumps(configuration),
        MODEL: "package ci\ncompiled: " + json.dumps(increment) + "\n",
        "parameters.toml": tomli_w.dumps(parameters),
    }
    original_paths = tuple(tmp_path.iterdir())
    with pytest.raises(ValueError, match="cue_compilation_failed:.*" + constraint):
        compile_projections(tmp_path, DECLARATION, files)
    assert tuple(tmp_path.iterdir()) == original_paths
