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
	node: {tools: {node: string, ...}, ...}
}
#Gate: {id: string, depends_on: *[] | [...string], ...}
_gateIDs: [for gate in _inputs.gate_registry.gates {gate.id}]
let githubView = github
let gitlabView = gitlab
let githubSourceSHA = "${{ github.event.pull_request.head.sha || github.sha }}"

// Bootstrap leaves the environment complete. An implicit re-sync would rebuild the editable
// project, and offline its isolated build cannot resolve the project's build requirements.
let offlineRun = "uv run --frozen --offline --no-sync"
let sourceCLI = "\(offlineRun) python -B -I -m ethos.cli"

// npm runs from the locked Node supply: the archive seed installs once, then the lock owns npm.
let nativeNpm = "python -B -m tools.ci.toolchain.npm"
let supplyDockerfile = ".config/ci/supply/Dockerfile"
let supplyImage = "ghcr.io/hengyangds/ethos-ci-supply:${{ github.sha }}"
let gitlabImage = "ghcr.io/hengyangds/ethos-ci-supply@sha256:e542b22f02b40110496b55ee0435539e9427d32a0167763503279d613993dde3"

// Commit-scoped GitLab jobs verify a commit once: a main push at dev's commit leaves them to
// the dev pipeline of the same commit, while commit-policy still admits every pushed ref.
let commitScopedRules = [{
	if: "$CI_COMMIT_BRANCH == \"main\""
	changes: {
		paths: ["**/*"]
		compare_to: "refs/heads/dev"
	}
}, {
	if:   "$CI_COMMIT_BRANCH == \"main\""
	when: "never"
}, {
	when: "on_success"
}]

// One bootstrap order for every Linux job: build-only dependencies make the editable source
// installable without build isolation, then the native tools, the npm seed, fixtures and trust.
let bootstrapCommands = {
	offline:   string
	isolation: string
	run:       string
	tools:     string
	npm:       string
	out: [
		"uv sync --locked\(offline) --no-install-project --group dev",
		"uv sync --locked\(offline)\(isolation) --group dev",
		"\(run) python -B -m tools.ci.toolchain.native --root . --mise\(tools)",
		"\(run) \(nativeNpm) --seed ci --ignore-scripts\(npm)",
		"\(run) python -B -I tools/ci/toolchain/fixture_supply.py .",
		"\(run) python -B -m tools.ci.toolchain.commit_trust",
	]
}
let githubBootstrap = (bootstrapCommands & {offline: "", isolation: "", run: "uv run --frozen", tools: " vale", npm: ""}).out
let githubBootstrapNames = [
	"Synchronize build-only Python dependencies",
	"Synchronize locked Python environment",
	"Prepare locked native tool supply",
	"Install locked npm packages",
	"Provision test fixture supply",
	"Bind operator commit trust",
]

// The immutable image is the offline supply; its manifest is checked against this checkout first.
let gitlabBootstrap = list.Concat([["sha256sum --check --quiet \"$ETHOS_CI_SUPPLY_MANIFEST\""], (bootstrapCommands & {
	offline:   " --offline"
	isolation: " --no-build-isolation"
	run:       offlineRun
	tools:     " vale gitleaks scc syft"
	npm:       " --offline"
}).out])
let githubPythonBootstrap = list.Concat([[{
	uses: "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
	with: {
		"fetch-depth": 0
		ref:           githubSourceSHA
	}
}, {
	uses: "astral-sh/setup-uv@07a047e608db84b3d8c06cd9a7c7dcc9c355c18e"
	with: {
		version:          "0.13.5"
		"python-version": "3.14"
	}
}, {
	name: "Provision native Python image supply"
	run:  "uv python install --no-bin 3.14"
}], [for index, command in githubBootstrap {
	name: githubBootstrapNames[index]
	run:  command
}]])

let releaseTagRef = "refs/tags/${{ inputs.release_tag }}"

// A release run is an explicit dispatch from accepted main naming one signed tag and its commit.
let regularRun = "!inputs.supply_image && !inputs.release_tag"
let releaseRun = "github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main' && inputs.release_tag != ''"
let releaseArguments = "--release --expect-head ${{ inputs.release_head }} --tag ${{ inputs.release_tag }}"

// The host-conformance supply order that every hosted OS proves: checkout, Python image,
// build-only dependencies, native and npm supply, then the project environment.
let githubHostSupplyAt = {
	checkout: string
	python:   string
	out: [{
		uses: "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
		with: {
			"fetch-depth": 0
			ref:           checkout
		}
	}, {
		uses: "astral-sh/setup-uv@07a047e608db84b3d8c06cd9a7c7dcc9c355c18e"
		with: {
			version:          "0.13.5"
			"python-version": python
		}
	}, {
		name: "Provision native Python image supply"
		run:  "uv python install --no-bin \(python)"
	}, {
		name: "Synchronize build-only Python dependencies"
		run:  "uv sync --locked --no-install-project --group dev"
	}, {
		name: "Prepare locked native build supply"
		env: PYTHONPATH: "src"
		run: "uv run --no-sync python -B tools/ci/toolchain/native.py --root . --mise vale"
	}, {
		name: "Install locked npm packages"
		env: PYTHONPATH: "src"
		run: "uv run --no-sync \(nativeNpm) --seed ci --ignore-scripts"
	}, {
		name: "Synchronize locked Python environment"
		run:  "uv sync --locked --group dev"
	}]
}

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
		workflow_dispatch: inputs: {
			supply_image: {
				description: "Build the locked Linux ARM64 CI supply image"
				required:    false
				type:        "boolean"
				default:     false
			}
			release_tag: {
				description: "Qualify and publish this signed pre-release tag"
				required:    false
				type:        "string"
				default:     ""
			}
			release_head: {
				description: "The exact commit that the release tag signs"
				required:    false
				type:        "string"
				default:     ""
			}
		}
	}
	permissions: contents: "read"
	env: #ExecutionEnvironment & {
		UV_CACHE_DIR:            "${{ github.workspace }}/build/runtime/tool-cache/uv"
		ETHOS_CI_TOOL_CACHE_DIR: "${{ github.workspace }}/build/runtime/tool-cache/ci-tools"
	}
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
				with: {
					"fetch-depth": 0
					ref:           githubSourceSHA
				}
			}, {
				// A build check reads every stage, so the smoke stage's named context must resolve.
				name: "Check the supply definition"
				run:  "docker buildx build --check --platform linux/arm64 --file \(supplyDockerfile) --build-context workspace=. ."
			}, {
				// The smoke stage runs this checkout offline as the image's unprivileged user.
				name: "Accept the supply offline against this checkout"
				run:  "docker buildx build --platform linux/arm64 --file \(supplyDockerfile) --target smoke --build-context workspace=. ."
			}, {
				name: "Build the supply image"
				run:  "docker buildx build --platform linux/arm64 --file \(supplyDockerfile) --target supply --tag \(supplyImage) --load ."
			}, {
				uses: "docker/login-action@81c6f93d4bc991e510b342a00b419b3bb4efc5c6"
				with: {
					registry: "ghcr.io"
					username: "${{ github.actor }}"
					password: "${{ secrets.GITHUB_TOKEN }}"
				}
			}, {
				name: "Publish the supply image"
				run:  "docker push \(supplyImage)"
			}, {
				name: "Inspect the published supply image"
				run:  "docker buildx imagetools inspect \(supplyImage)"
			}]
		}
		"host-conformance": {
			name:      "${{ matrix.os }} / Python ${{ matrix.python }}"
			"runs-on": "${{ matrix.os }}"
			if:        "${{ \(regularRun) }}"
			env: UV_PYTHON_INSTALL_DIR: "${{ github.workspace }}/build/runtime/python"
			strategy: {
				"fail-fast": false
				matrix: {
					os: ["ubuntu-latest", "windows-latest", "macos-latest"]
					python: ["3.12", "3.13", "3.14"]
				}
			}
			steps: list.Concat([(githubHostSupplyAt & {checkout: githubSourceSHA, python: "${{ matrix.python }}"}).out, [{
				name: "Execute wheel conformance"
				run:  "uv run --frozen python -m nox -s host_conformance"
			}, {
				name: "Execute npm launcher"
				run:  "uv run --frozen \(nativeNpm) run ethos -- --version"
			}, {
				name: "Execute native npm package tests"
				run:  "uv run --frozen python -m nox -s javascript_tests"
			}, {
				name: "Upload host conformance receipt"
				if:   "always()"
				uses: "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9"
				with: {
					name:                "host-conformance-${{ matrix.os }}-py${{ matrix.python }}"
					path:                "build/evidence/local-install/smoke.json"
					"if-no-files-found": "error"
				}
			}]])
		}
		quality: {
			name:      "quality gates"
			"runs-on": "ubuntu-24.04-arm"
			if:        "${{ \(regularRun) }}"
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
				name: "HEAD-bound hosted verification receipt"
				run:  "\(offlineRun) python -m nox -s hosted_verification"
			}, {
				name: "Upload proof receipt"
				if:   "always()"
				uses: "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9"
				with: {
					name: "ethos-proof-receipt"
					path: """
						build/evidence/quality/proof/
						build/evidence/quality/tests/pytest/junit*.xml
						build/evidence/quality/tests/coverage/coverage.xml
						build/evidence/quality/tests/allure/

						"""
					"if-no-files-found": "error"
				}
			}, {
				uses: "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9"
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
			if:                  "${{ \(regularRun) }}"
			"continue-on-error": true
			steps: list.Concat([githubPythonBootstrap, [{
				name: "External links"
				run:  "\(offlineRun) python -m nox -s external_links"
			}, {
				name: "Upload external link observation"
				if:   "always()"
				uses: "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9"
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
			if:        "${{ always() && \(regularRun) }}"
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
			if:        "${{ always() && \(regularRun) }}"
			steps: [{
				name: "Require successful hosted execution and artifact publication"
				env: QUALITY_RESULT: "${{ needs.quality.result }}"
				run: "test \"$QUALITY_RESULT\" = success"
			}]
		}
		// The signed tag admits each build: a runner holds no repository proof. The wheel carries
		// its platform's Node and Vale, so every platform builds and qualifies its own wheel and
		// retains it beside the archive its release smoke built.
		"release-platforms": {
			name:      "release runtime ${{ matrix.os }}"
			"runs-on": "${{ matrix.os }}"
			if:        "${{ \(releaseRun) }}"
			// Windows remains an optional platform until its delivered artifact qualifies.
			"continue-on-error": "${{ matrix.os == 'windows-latest' }}"
			env: {
				ETHOS_COMMIT_ALLOWED_SIGNERS: "${{ vars.ETHOS_COMMIT_ALLOWED_SIGNERS }}"
				UV_PYTHON_INSTALL_DIR:        "${{ github.workspace }}/build/runtime/python"
			}
			strategy: {
				"fail-fast": false
				matrix: os: ["ubuntu-latest", "ubuntu-24.04-arm", "macos-latest", "windows-latest"]
			}
			steps: list.Concat([(githubHostSupplyAt & {checkout: releaseTagRef, python: "3.14"}).out, [{
				name: "Bind operator commit trust"
				run:  "uv run --frozen python -B -m tools.ci.toolchain.commit_trust"
			}, {
				name: "Build the release wheel its signed tag admits"
				run:  "uv run --frozen python -m nox -s build -- \(releaseArguments)"
			}, {
				name: "Qualify the release wheel and retain its runtime archive"
				run:  "uv run --frozen python -m nox -s install_smoke -- \(releaseArguments)"
			}, {
				uses: "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9"
				with: {
					name: "release-runtime-${{ matrix.os }}"
					path: """
						build/artifacts/release/python/
						build/artifacts/native/
						build/evidence/local-install/release-smoke.json

						"""
					"if-no-files-found": "error"
				}
			}]])
		}
		"release-publish": {
			name:      "release publication"
			"runs-on": "ubuntu-latest"
			needs:     "release-platforms"
			if:        "${{ !cancelled() && \(releaseRun) }}"
			permissions: contents: "write"
			steps: [{
				uses: "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
				with: ref: releaseTagRef
			}, {
				uses: "astral-sh/setup-uv@07a047e608db84b3d8c06cd9a7c7dcc9c355c18e"
				with: {
					version:          "0.13.5"
					"python-version": "3.14"
				}
			}, {
				uses: "actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333"
				with: path: "build/release/inputs"
			}, {
				// The assembler admits only archives whose qualification evidence matches their bytes.
				name: "Assemble the qualified release assets"
				run:  "uv run --no-project python -B -I tools/ci/delivery/release_assets.py --tag ${{ inputs.release_tag }} --source build/release/inputs --output build/release/out --base-url https://github.com/${{ github.repository }}/releases/download/${{ inputs.release_tag }} --changelog CHANGELOG.md"
			}, {
				name: "Publish the signed pre-release"
				env: GH_TOKEN: "${{ github.token }}"
				run: "gh release create ${{ inputs.release_tag }} --repo ${{ github.repository }} --prerelease --verify-tag --title \"ETHOS ${{ inputs.release_tag }}\" --notes-file build/release/out/notes.md build/release/out/assets/*"
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
		// The runner gives the checkout to the image's unprivileged user instead of a zero umask.
		FF_DISABLE_UMASK_FOR_DOCKER_EXECUTOR: "true"
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
		image:         gitlabImage
		before_script: gitlabBootstrap
		stage:         "quality"
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
		image:         gitlabImage
		before_script: gitlabBootstrap
		stage:         "verify"
		rules:         commitScopedRules
		script: ["\(offlineRun) python -m nox -s host_conformance"]
		artifacts: {
			when: "always"
			paths: ["build/evidence/local-install/smoke.json"]
		}
	}
	"ethos:verify": {
		image:         gitlabImage
		before_script: gitlabBootstrap
		stage:         "verify"
		rules:         commitScopedRules
		variables: {
			// GIT_DEPTH=0 does not repair a runner checkout that was previously
			// shallow. Reclone this history-sensitive execution owner so replay can
			// resolve pinned commits without repeating preparation for every gate.
			GIT_STRATEGY: "clone"
			// Scoped native process observation removes unrelated descriptor churn.
			// Qualify four workers through the full hosted proof and coverage floor.
			// The image's unprivileged user runs the entire job, preserving process
			// visibility and permission tests.
			ETHOS_TEST_WORKERS: "4"
		}
		script: [
			"\(offlineRun) python -m nox -s hosted_verification",
		]
		// GitHub retains raw Allure results; GitLab's instance artifact limit cannot hold them.
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
		rules:         commitScopedRules
		allow_failure: true
		before_script: gitlabBootstrap
		script: ["\(offlineRun) python -m nox -s external_links"]
		artifacts: {
			when: "always"
			paths: ["build/evidence/quality/external-links/report.json"]
		}
	}
	"ethos:npm": {
		stage: "verify"
		rules: commitScopedRules
		variables: NODE_VERSION: _inputs.node.tools.node
		// The shared cache preparer owns Node; Nox owns package test execution.
		image:         gitlabImage
		before_script: gitlabBootstrap
		script: [
			"\(offlineRun) \(nativeNpm) run ethos -- --version",
			"\(offlineRun) python -m nox -s javascript_tests",
		]
	}
}

#ExecutionEnvironment: {
	...
	PYTHONWARNINGS:          "error"
	UV_LINK_MODE:            "copy"
	UV_CACHE_DIR:            string
	ETHOS_CI_TOOL_CACHE_DIR: string
}
