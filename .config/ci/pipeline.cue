package ci

import (
	"list"
)

// Native gate and Node declarations remain owners of their respective facts.
// The compiler supplies exact inputs; there is no second gate list in this model.
_inputs: {
	gate_registry: {
		gates: [#Gate, ...#Gate]
		proof_sets: full: [string, ...string]
		...
	}
	node: {default_version: string, compatibility_versions: [string, ...string], ...}
}
#Gate: {id: string, depends_on: *[] | [...string], ...}
_gateIDs: [for gate in _inputs.gate_registry.gates {gate.id}]
let githubView = github
let gitlabView = gitlab
let sourceCLI = "uv run --frozen --offline python -B -I -m ethos.cli"
let externalLinkCommand = "tools/ci/scripts/with-python-runtime.sh -- \(sourceCLI) prove --host --execute --gate external-links --expect-head \"$(git rev-parse HEAD)\" --json"
let gitlabImage = "ghcr.io/hengyangds/ethos-ci-supply@sha256:72e2434cbc0ac30cce6c312618c51beb290a214f4e60b0af51af95a79c0dce0f"
let githubPythonBootstrap = [{
	uses: "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
	with: "fetch-depth": 0
}, {
	uses: "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97"
	with: "python-version": "3.14"
}, {
	uses: "astral-sh/setup-uv@bec219d24cd3e171d82865faccec33120bb574f4"
	with: version: "0.12.16"
}, {
	name: "Bootstrap Python and OpenSpec"
	run:  "tools/ci/scripts/bootstrap-python.sh"
}]

compiled: {
	checks: {
		uniqueGates: true & list.UniqueItems(_gateIDs)
		uniqueFull:  true & list.UniqueItems(_inputs.gate_registry.proof_sets.full)
		for id in _inputs.gate_registry.proof_sets.full {
			"full:\(id)": true & list.Contains(_gateIDs, id)
		}
		for gate in _inputs.gate_registry.gates {
			for dependency in gate.depends_on {
				"dependency:\(gate.id):\(dependency)": true & list.Contains(_gateIDs, dependency)
			}
		}
	}
	providers: {github: githubView, gitlab: gitlabView}
}

github: {
	name: "ETHOS CI"
	on: {
		pull_request: null
		push: branches: [
			"dev",
			"main",
			"proposal/**",
		]
		workflow_dispatch: inputs: supply_image: {
			description: "Build the locked Linux ARM64 CI supply image"
			required:    false
			type:        "boolean"
			default:     false
		}
	}
	permissions: contents: "read"
	env: #ExecutionEnvironment
	jobs: {
		"supply-image": {
			name:      "locked Linux ARM64 supply"
			if:        "${{ github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/dev' && inputs.supply_image }}"
			"runs-on": "ubuntu-24.04-arm"
			permissions: {
				contents: "read"
				packages: "write"
			}
			steps: [{
				uses: "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
				with: "fetch-depth": 0
			}, {
				name: "Build and publish immutable supply"
				env: GHCR_TOKEN: "${{ secrets.GITHUB_TOKEN }}"
				run: """
					set -euo pipefail
					image="ghcr.io/hengyangds/ethos-ci-supply:${{ github.sha }}"
					docker buildx build --check --platform linux/arm64 --file .config/ci/supply/Dockerfile .
					docker build --platform linux/arm64 --file .config/ci/supply/Dockerfile --tag "$image" .
					smoke_root="$(mktemp -d)"
					smoke_name="ethos-ci-supply-${{ github.run_id }}"
					export DOCKER_CONFIG="$smoke_root/docker-config"
					mkdir -m 0700 "$DOCKER_CONFIG"
					cleanup() {
					  docker rm -f "$smoke_name" >/dev/null 2>&1 || true
					  rm -rf "$smoke_root"
					}
					trap cleanup EXIT
					git clone --local --no-hardlinks --no-checkout . "$smoke_root/repo"
					git -C "$smoke_root/repo" checkout --detach "${{ github.sha }}"
					smoke_command=(docker create --name "$smoke_name" --network none)
					smoke_command+=(--env CI_PROJECT_DIR=/workspace --env ETHOS_CI_SUPPLY_MANIFEST=/opt/ethos-supply/input.sha256)
					smoke_command+=(--env GIT_CONFIG_COUNT=1 --env GIT_CONFIG_KEY_0=safe.directory --env GIT_CONFIG_VALUE_0=/workspace)
					smoke_command+=(--entrypoint /workspace/tools/ci/scripts/bootstrap-python.sh "$image" -- /bin/bash -lc "test \\$EUID -eq 65534 && uv run --frozen --offline python -B -I -m ethos.cli --version")
					"${smoke_command[@]}"
					docker cp "$smoke_root/repo/." "$smoke_name:/workspace"
					docker start --attach "$smoke_name"
					test "$(docker inspect --format '{{.State.ExitCode}}' "$smoke_name")" = 0
					docker rm "$smoke_name"
					printf '%s' "$GHCR_TOKEN" | docker login ghcr.io --username "${{ github.actor }}" --password-stdin
					docker push "$image"
					docker buildx imagetools inspect "$image"
					cleanup
					trap - EXIT
					"""
			}]
		}
		"host-conformance": {
			name:      "${{ matrix.os }} / Python ${{ matrix.python }}"
			"runs-on": "${{ matrix.os }}"
			if:        "${{ !inputs.supply_image }}"
			env: UV_PYTHON_INSTALL_DIR: "${{ github.workspace }}/build/runtime/python"
			strategy: {
				"fail-fast": false
				matrix: {
					os: ["ubuntu-latest", "windows-latest", "macos-latest"]
					python: ["3.12", "3.13", "3.14"]
				}
			}
			steps: [{
				uses: "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
				with: "fetch-depth": 0
			}, {
				uses: "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020"
				with: {
					"node-version": _inputs.node.default_version
					cache:          "npm"
				}
			}, {
				uses: "astral-sh/setup-uv@bec219d24cd3e171d82865faccec33120bb574f4"
				with: {
					version:          "0.12.16"
					"python-version": "${{ matrix.python }}"
				}
			}, {
				name: "Provision native Python image supply"
				run:  "uv python install --no-bin ${{ matrix.python }}"
			}, {
				name: "Install locked runtimes"
				run:  "npm ci --ignore-scripts"
			}, {
				name: "Synchronize locked Python environment"
				run:  "uv sync --locked --group dev"
			}, {
				name: "Execute wheel conformance"
				run:  "uv run --frozen python -m nox -s host_conformance"
			}, {
				name: "Upload host conformance receipt"
				if:   "always()"
				uses: "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
				with: {
					name:                "host-conformance-${{ matrix.os }}-py${{ matrix.python }}"
					path:                "build/evidence/local-install/smoke.json"
					"if-no-files-found": "error"
				}
			}]
		}
		quality: {
			name:      "quality gates"
			"runs-on": "macos-latest"
			if:        "${{ !inputs.supply_image }}"
			env: ETHOS_COMMIT_ALLOWED_SIGNERS: "${{ vars.ETHOS_COMMIT_ALLOWED_SIGNERS }}"
			steps: list.Concat([githubPythonBootstrap, [{
				name: "Admit pushed commit range"
				if:   "github.event_name == 'push'"
				run:  "\(sourceCLI) hook commit-range --target-ref \"${{ github.ref }}\" --proposed-head \"${{ github.sha }}\" --remote-head \"${{ github.event.before }}\" --remote origin --root . --json"
			}, {
				name: "Admit pull request commit range"
				if:   "github.event_name == 'pull_request'"
				run:  "\(sourceCLI) hook commit-range --target-ref \"refs/heads/${{ github.event.pull_request.base.ref }}\" --proposed-head \"${{ github.event.pull_request.head.sha }}\" --remote-head \"${{ github.event.pull_request.base.sha }}\" --remote origin --root . --json"
			}, {
				// The registry owns gate order and package creation. Execute it once;
				// independently required hosted checks below project this exact result.
				name: "Hosted provider observation envelope"
				run:  "uv run --frozen --offline python -m nox -s hosted_observation"
			}, {
				name: "HEAD-bound hosted verification receipt"
				run:  "tools/ci/scripts/run-head-bound-proof.sh"
			}, {
				name: "Upload proof receipt"
				if:   "always()"
				uses: "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
				with: {
					name: "ethos-proof-receipt"
					path: """
						build/evidence/quality/proof/
						build/evidence/quality/tests/pytest/junit*.xml
						build/evidence/quality/tests/coverage/coverage.xml

						"""
					"if-no-files-found": "error"
				}
			}, {
				uses: "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
				with: {
					name:                "python-distributions"
					"if-no-files-found": "error"
					path: """
						build/artifacts/python/
						build/evidence/release/

						"""
				}
			}]])
		}
		"external-links": {
			name:                "external link health"
			"runs-on":           "ubuntu-latest"
			if:                  "${{ !inputs.supply_image }}"
			"continue-on-error": true
			steps: list.Concat([githubPythonBootstrap, [{
				name: "External links"
				run:  "mkdir -p build/evidence/quality/external-links\n\(externalLinkCommand) > build/evidence/quality/external-links/report.json"
			}, {
				name: "Upload external link observation"
				if:   "always()"
				uses: "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
				with: {
					name:                "ethos-external-link-health"
					path:                "build/evidence/quality/external-links/report.json"
					"if-no-files-found": "error"
				}
			}]])
		}
		verify: {
			name:      "repository proof"
			"runs-on": "ubuntu-latest"
			needs:     "quality"
			if:        "${{ always() && !inputs.supply_image }}"
			steps: [{
				name: "Require successful hosted execution and artifact publication"
				env: QUALITY_RESULT: "${{ needs.quality.result }}"
				run: "test \"$QUALITY_RESULT\" = success"
			}]
		}
		package: {
			name:      "package artifacts"
			"runs-on": "ubuntu-latest"
			needs:     "quality"
			if:        "${{ always() && !inputs.supply_image }}"
			steps: [{
				name: "Require successful hosted execution and artifact publication"
				env: QUALITY_RESULT: "${{ needs.quality.result }}"
				run: "test \"$QUALITY_RESULT\" = success"
			}]
		}
	}
}

gitlab: {
	stages: [
		"quality",
		"verify",
	]

	// Candidate integration is local-only. Hosted pipelines run only for remote-eligible
	// branches, plus merge-request validation.
	workflow: {
		rules: [{
			if: "$CI_PIPELINE_SOURCE == \"merge_request_event\""
		}, {
			if: "$CI_COMMIT_BRANCH == \"dev\" || $CI_COMMIT_BRANCH == \"main\" || $CI_COMMIT_BRANCH =~ /^proposal\\/.+$/"
		}, {
			when: "never"
		}]
	}
	variables: #ExecutionEnvironment & {
		// Full history keeps Git-derived ancestry and evidence checks available.
		GIT_DEPTH:                "0"
		UV_CACHE_DIR:             "/opt/ethos-supply/uv-cache"
		ETHOS_CI_TOOL_CACHE_DIR:  "/opt/ethos-supply/tool-cache"
		UV_PYTHON_INSTALL_DIR:    "/opt/ethos-supply/python"
		NPM_CONFIG_CACHE:         "/opt/ethos-supply/npm-cache"
		ETHOS_CI_SUPPLY_MANIFEST: "/opt/ethos-supply/input.sha256"
	}

	// Auto-retry every job on infrastructure failures only (image-pull timeouts to
	// Docker Hub, runner crashes, API hiccups) — the runner's egress to external
	// registries is intermittently flaky, and a governance gate that goes red on a
	// transient pull is noise, not a real breach. Never retries script_failure, so a
	// genuine gate breach still fails the pipeline.
	default: {
		tags: ["${ETHOS_GITLAB_RUNNER_TAG}"]
		retry: {
			max: 2
			when: [
				"runner_system_failure",
				"stuck_pending_with_matching_runners",
				"stuck_pending_no_matching_runners",
				"no_updates_running",
				"no_updates_canceling",
				"api_failure",
				"scheduler_failure",
			]
		}
	}

	// The full registry owns quality, proof, package creation and SBOM once.
	// Commit admission and native host/Node conformance retain their own boundaries.
	"ethos:commit-policy": {
		image: gitlabImage
		before_script: ["tools/ci/scripts/bootstrap-python.sh"]
		stage: "quality"
		variables: GIT_STRATEGY: "clone"
		rules: [{
			if: "$CI_PIPELINE_SOURCE == \"push\""
			variables: {
				ETHOS_COMMIT_TARGET_REF:    "refs/heads/${CI_COMMIT_BRANCH}"
				ETHOS_COMMIT_PROPOSED_HEAD: "${CI_COMMIT_SHA}"
				ETHOS_COMMIT_REMOTE_HEAD:   "${CI_COMMIT_BEFORE_SHA}"
			}
		}, {
			if: "$CI_PIPELINE_SOURCE == \"merge_request_event\" && $CI_MERGE_REQUEST_SOURCE_BRANCH_SHA && $CI_MERGE_REQUEST_TARGET_BRANCH_SHA"
			variables: {
				ETHOS_COMMIT_TARGET_REF:    "refs/heads/${CI_MERGE_REQUEST_TARGET_BRANCH_NAME}"
				ETHOS_COMMIT_PROPOSED_HEAD: "${CI_MERGE_REQUEST_SOURCE_BRANCH_SHA}"
				ETHOS_COMMIT_REMOTE_HEAD:   "${CI_MERGE_REQUEST_TARGET_BRANCH_SHA}"
			}
		}, {
			if: "$CI_PIPELINE_SOURCE == \"merge_request_event\" && $CI_MERGE_REQUEST_DIFF_BASE_SHA"
			variables: {
				ETHOS_COMMIT_TARGET_REF:    "refs/heads/${CI_MERGE_REQUEST_TARGET_BRANCH_NAME}"
				ETHOS_COMMIT_PROPOSED_HEAD: "${CI_COMMIT_SHA}"
				ETHOS_COMMIT_REMOTE_HEAD:   "${CI_MERGE_REQUEST_DIFF_BASE_SHA}"
			}
		}, {
			when: "never"
		}]
		script: ["\(sourceCLI) hook commit-range --target-ref \"${ETHOS_COMMIT_TARGET_REF}\" --proposed-head \"${ETHOS_COMMIT_PROPOSED_HEAD}\" --remote-head \"${ETHOS_COMMIT_REMOTE_HEAD}\" --remote origin --root . --json"]
	}
	"ethos:host-conformance": {
		image: gitlabImage
		before_script: ["tools/ci/scripts/bootstrap-python.sh"]
		stage: "verify"
		script: ["uv run --frozen --offline python -m nox -s host_conformance"]
		artifacts: {
			when: "always"
			paths: ["build/evidence/local-install/smoke.json"]
		}
	}
	"ethos:verify": {
		image: {
			name: gitlabImage
			entrypoint: [
				"bash",
				"-c",
				"exec \"$CI_PROJECT_DIR/tools/ci/scripts/bootstrap-python.sh\" -- \"$@\"",
				"ethos-ci-entrypoint",
			]
		}
		before_script: []
		stage: "verify"
		variables: {
			// GIT_DEPTH=0 does not repair a runner checkout that was previously
			// shallow. Reclone this history-sensitive execution owner so replay can
			// resolve pinned commits without repeating preparation for every gate.
			GIT_STRATEGY: "clone"
			// The arm64 hosted runner can terminate xdist workers under the full
			// coverage suite. Keep the reusable owner script and its default parallel
			// capability intact; this hosted projection deliberately runs one worker.
			// The entrypoint prepares the image and then replaces PID 1. The entire
			// job runs unprivileged, preserving process visibility and permission tests.
			ETHOS_TEST_WORKERS: "1"
		}
		script: [
			"uv run --frozen --offline python -m nox -s hosted_observation",
			"tools/ci/scripts/run-head-bound-proof.sh",
		]
		artifacts: {
			when: "always"
			paths: [
				"build/evidence/quality/proof/",
				"build/evidence/quality/tests/pytest/junit*.xml",
				"build/evidence/quality/tests/coverage/coverage.xml",
				"build/evidence/quality/security/",
				"build/evidence/quality/secrets/",
				"build/artifacts/python/",
				"build/evidence/release/",
			]
			reports: {
				junit: "build/evidence/quality/tests/pytest/junit*.xml"
				coverage_report: {
					coverage_format: "cobertura"
					path:            "build/evidence/quality/tests/coverage/coverage.xml"
				}
			}
		}
	}
	"ethos:external-links": {
		image:         gitlabImage
		stage:         "verify"
		allow_failure: true
		before_script: ["tools/ci/scripts/bootstrap-python.sh"]
		script: [
			"mkdir -p build/evidence/quality/external-links",
			"\(externalLinkCommand) > build/evidence/quality/external-links/report.json",
		]
		artifacts: {
			when: "always"
			paths: ["build/evidence/quality/external-links/report.json"]
		}
	}
	"ethos:npm": {
		stage: "verify"
		parallel: matrix: [{
			NODE_VERSION: _inputs.node.compatibility_versions
		}]
		// Runs on python:3.14 with exact Node
		// releases installed from nodejs.org; see the runtime policy and installer.
		image: gitlabImage
		script: [
			"tools/ci/scripts/bootstrap-python.sh",
			"tools/ci/scripts/install-node.sh",
			"tools/ci/scripts/run-node-compatibility.sh",
		]
	}
}

#ExecutionEnvironment: {
	...
	PYTHONWARNINGS:          "error"
	UV_LINK_MODE:            "copy"
	UV_CACHE_DIR:            *"build/runtime/tool-cache/uv" | string
	ETHOS_CI_TOOL_CACHE_DIR: *"build/runtime/tool-cache/ci-tools" | string
}
