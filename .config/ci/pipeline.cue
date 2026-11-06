package ci

import (
	"encoding/json"
	"list"
	"strings"
)

// Native gate and Node declarations remain owners of their respective facts.
// The compiler supplies exact inputs; there is no second gate list in this model.
_inputs: {
	gate_registry: {
		gates: [#Gate, ...#Gate]
		proof_sets: full: [string, ...string]
		...
	}
	mise: {tools: {node: string, uv: string, ...}, ...}
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
let gitlabImage = "ghcr.io/hengyangds/ethos-ci-supply@sha256:36acefde2cda6b0724d9fe72c08e83a55c339b63504791507f41f3fd93834ef6"

// The commit the bound image was built from; the CI projection check compares its manifest inputs.
let gitlabImageSource = "690e75069775cb2b70b96a102ebf0ad782f6cafb"

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
	uses: "astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2"
	with: {
		version:          _inputs.mise.tools.uv
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
let regularRun = "!inputs.supply_image && !inputs.release_tag && !inputs.journey_tag && !inputs.scan_tag"
let releaseRun = "github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main' && inputs.release_tag != ''"
let releaseArguments = "--release --expect-head ${{ inputs.release_head }} --tag ${{ inputs.release_tag }}"

// A journey run qualifies one already published pre-release again, with the dispatching ref's code.
let journeyRun = "github.event_name == 'workflow_dispatch' && inputs.journey_tag != ''"

// A scan run reports one already published release's advisories again from its inventories.
let scanRun = "github.event_name == 'workflow_dispatch' && inputs.scan_tag != ''"

// A main push moves main to the accepted commit that dev's run of the same commit verifies, so it
// repeats none of the commit-scoped jobs and only admits its pushed range (decision D11).
let mainPush = "github.event_name == 'push' && github.ref == 'refs/heads/main'"
let commitRun = "\(regularRun) && !(\(mainPush))"
let pushedRange = "\(sourceCLI) hook commit-range --target-ref \"${{ github.ref }}\" --proposed-head \"${{ github.sha }}\" --remote-head \"${{ github.event.before }}\" --remote origin --root . --json"

// A newer push of a proposal ref replaces the head that its earlier run verifies, so that run is
// cancelled. Every other run has a group of its own and never waits for or cancels another.
let proposalPush = "github.event_name == 'push' && startsWith(github.ref, 'refs/heads/proposal/')"
let concurrencyGroup = "\(proposalPush) && format('{0}-{1}', github.workflow, github.ref) || format('{0}-run-{1}', github.workflow, github.run_id)"

// Windows on Arm executes the x64 runtime through its emulation; CEL ships no win_arm64 wheel.
let windowsArmLeg = {os: "windows-11-arm", python: "cpython-3.14-windows-x86_64-none"}

// Each release leg qualifies the one host platform it declares, on the runner that provides it.
// A required platform must publish; an optional one is left out and named when its leg fails.
// An emulated leg publishes no wheel, so it cannot stand in for a required platform.
let releaseLegs = [
	{host: "linux-x64", os: "ubuntu-latest", python: "3.14", required: true, emulated: false},
	{host: "linux-arm64", os: "ubuntu-24.04-arm", python: "3.14", required: true, emulated: false},
	{host: "macos-arm64", os: "macos-latest", python: "3.14", required: true, emulated: false},
	{host: "windows-x64", os: "windows-latest", python: "3.14", required: false, emulated: false},
	windowsArmLeg & {host: "windows-arm64", required: false, emulated: true},
]
let releaseLegRun = "${{ contains(fromJSON('\(json.Marshal([for leg in releaseLegs {"\(leg.os) \(leg.python)"}]))'), format('{0} {1}', matrix.os, matrix.python)) }}"
let releaseHosts = "--required \(strings.Join([for leg in releaseLegs if leg.required {leg.host}], ",")) --optional \(strings.Join([for leg in releaseLegs if !leg.required {leg.host}], ","))"

// The adopter journey runs from the published artifacts on the platforms a beta must qualify.
let journeyLegs = [for leg in releaseLegs if leg.host == "linux-x64" || leg.host == "macos-arm64" {leg}]

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
		uses: "astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2"
		with: {
			version:          _inputs.mise.tools.uv
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
		uniqueReleaseHosts: true & list.UniqueItems([for leg in releaseLegs {leg.host}])
		for leg in releaseLegs if leg.required {
			"release-required-native:\(leg.host)": true & !leg.emulated
		}
		for leg in journeyLegs {
			"journey-leg-required:\(leg.host)": true & leg.required
		}
		uniqueFull: true & list.UniqueItems(_inputs.gate_registry.proof_sets.full)
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
			journey_tag: {
				description: "Qualify this published pre-release on the adopter journey alone"
				required:    false
				type:        "string"
				default:     ""
			}
			journey_previous: {
				description: "Comma-separated earlier published pre-release tags that the journey upgrades from; empty selects the latest earlier published release"
				required:    false
				type:        "string"
				default:     ""
			}
			scan_tag: {
				description: "Report the binary advisories of this published release's inventories alone"
				required:    false
				type:        "string"
				default:     ""
			}
		}
	}
	permissions: contents: "read"
	concurrency: {
		group:                "${{ \(concurrencyGroup) }}"
		"cancel-in-progress": true
	}
	env: #ExecutionEnvironment & {
		UV_CACHE_DIR:            "${{ github.workspace }}/build/runtime/tool-cache/uv"
		ETHOS_CI_TOOL_CACHE_DIR: "${{ github.workspace }}/build/runtime/tool-cache/ci-tools"
	}
	jobs: {
		"supply-image": {
			name: "locked Linux ARM64 supply"
			// A lane that changes a hashed supply input builds its image from its proposal ref, so the
			// binding lands with that input and GitLab never verifies a head without its supply.
			if:        "${{ github.event_name == 'workflow_dispatch' && (github.ref == 'refs/heads/dev' || startsWith(github.ref, 'refs/heads/proposal/')) && inputs.supply_image }}"
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
		"commit-policy": {
			name:      "commit policy"
			"runs-on": "ubuntu-24.04-arm"
			if:        "${{ \(mainPush) }}"
			env: ETHOS_COMMIT_ALLOWED_SIGNERS: "${{ vars.ETHOS_COMMIT_ALLOWED_SIGNERS }}"
			steps: list.Concat([githubPythonBootstrap, [{
				name: "Admit pushed commit range"
				run:  pushedRange
			}]])
		}
		"host-conformance": {
			name:      "${{ matrix.os }} / Python ${{ matrix.python }}"
			"runs-on": "${{ matrix.os }}"
			if:        "${{ \(commitRun) }}"
			env: UV_PYTHON_INSTALL_DIR: "${{ github.workspace }}/build/runtime/python"
			strategy: {
				"fail-fast": false
				matrix: {
					os: ["ubuntu-latest", "windows-latest", "macos-latest"]
					python: ["3.12", "3.13", "3.14"]
					// A proposal push leaves its slowest pair, Windows on Arm, to dev's run of the
					// landed commit, which is the proposal's exact commit.
					include: "${{ fromJSON(\(proposalPush) && '[]' || '\(json.Marshal([windowsArmLeg]))') }}"
				}
			}
			steps: list.Concat([(githubHostSupplyAt & {checkout: githubSourceSHA, python: "${{ matrix.python }}"}).out, [{
				name: "Execute wheel conformance"
				run:  "uv run --frozen python -m nox -s host_conformance"
			}, {
				// A leg on a release leg's runner and Python catalogs the archive its smoke kept, as the
				// release leg will, so the release's inventory step never first runs at release time. Its
				// log carries the evidence, including any component declared from the locked supply.
				name: "Declare the components of the kept runtime archive"
				if:   releaseLegRun
				run:  "uv run --frozen python -m nox -s supply_chain"
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
					name: "host-conformance-${{ matrix.os }}-py${{ matrix.python }}"
					path: """
						build/evidence/local-install/smoke.json
						build/evidence/local-install/smoke.events.jsonl
						"""
					"if-no-files-found": "error"
				}
			}]])
		}
		quality: {
			name:      "quality gates"
			"runs-on": "ubuntu-24.04-arm"
			if:        "${{ \(commitRun) }}"
			env: ETHOS_COMMIT_ALLOWED_SIGNERS: "${{ vars.ETHOS_COMMIT_ALLOWED_SIGNERS }}"
			steps: list.Concat([githubPythonBootstrap, [{
				name: "Admit pushed commit range"
				if:   "github.event_name == 'push'"
				run:  pushedRange
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
			if:                  "${{ \(commitRun) }}"
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
			if:        "${{ always() && \(commitRun) }}"
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
			if:        "${{ always() && \(commitRun) }}"
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
			name:      "release runtime ${{ matrix.host }}"
			"runs-on": "${{ matrix.os }}"
			if:        "${{ \(releaseRun) }}"
			// Only a leg that the declaration marks optional may fail without failing the run.
			"continue-on-error": "${{ !matrix.required }}"
			env: {
				ETHOS_COMMIT_ALLOWED_SIGNERS: "${{ vars.ETHOS_COMMIT_ALLOWED_SIGNERS }}"
				UV_PYTHON_INSTALL_DIR:        "${{ github.workspace }}/build/runtime/python"
			}
			strategy: {
				"fail-fast": false
				matrix: {
					host: [for leg in releaseLegs {leg.host}]
					include: releaseLegs
				}
			}
			steps: list.Concat([(githubHostSupplyAt & {checkout: releaseTagRef, python: "${{ matrix.python }}"}).out, [{
				name: "Bind operator commit trust"
				run:  "uv run --frozen python -B -m tools.ci.toolchain.commit_trust"
			}, {
				name: "Build the release wheel its signed tag admits"
				run:  "uv run --frozen python -m nox -s build -- \(releaseArguments)"
			}, {
				name: "Qualify the release wheel and retain its runtime archive"
				run:  "uv run --frozen python -m nox -s install_smoke -- \(releaseArguments)"
			}, {
				// Syft reads the kept archive here, in a job without write permission.
				name: "Declare the components of the retained runtime archive"
				run:  "uv run --frozen python -m nox -s supply_chain -- --host ${{ matrix.host }}"
			}, {
				uses: "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9"
				with: {
					name: "release-runtime-${{ matrix.host }}"
					path: """
						build/artifacts/release/python/
						build/artifacts/native/
						build/evidence/local-install/release-smoke.json
						build/evidence/release/runtime.spdx.json
						build/evidence/release/runtime.syft.json

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
			permissions: {
				contents:     "write"
				"id-token":   "write"
				attestations: "write"
			}
			steps: [{
				uses: "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
				with: ref: releaseTagRef
			}, {
				uses: "astral-sh/setup-uv@68559e99cc807c1eb7e9238fd43a15bba460eec2"
				with: {
					version:          _inputs.mise.tools.uv
					"python-version": "3.14"
				}
			}, {
				uses: "actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333"
				with: path: "build/release/inputs"
			}, {
				// The assembler admits only archives whose qualification evidence matches their bytes.
				name: "Assemble the qualified release assets"
				run:  "uv run --no-project python -B -I tools/ci/delivery/release_assets.py --tag ${{ inputs.release_tag }} --source build/release/inputs --output build/release/out --base-url https://github.com/${{ github.repository }}/releases/download/${{ inputs.release_tag }} --changelog CHANGELOG.md --expect-head ${{ inputs.release_head }} \(releaseHosts)"
			}, {
				// Mise's github backend verifies these attestations when it installs a pinned release;
				// they also bind each runtime archive's two inventories to the release workflow.
				name: "Attest the release archives and wheels"
				uses: "actions/attest-build-provenance@4d101475d8b20a2381f78447822ac1eab6504dd8"
				with: "subject-path": "build/release/out/assets/ethos-*.tar.gz\nbuild/release/out/assets/ethos-*.whl\nbuild/release/out/assets/ethos-*.spdx.json\nbuild/release/out/assets/ethos-*.syft.json"
			}, {
				name: "Publish the signed pre-release"
				env: GH_TOKEN: "${{ github.token }}"
				run: "gh release create ${{ inputs.release_tag }} --repo ${{ github.repository }} --prerelease --verify-tag --title \"ETHOS ${{ inputs.release_tag }}\" --notes-file build/release/out/notes.md build/release/out/assets/*"
			}]
		}
		// Grype reads only the inventories the release published; its report never blocks it.
		"release-binary-scan": {
			name:                "release binary scan"
			"runs-on":           "ubuntu-latest"
			needs:               "release-publish"
			if:                  "${{ !cancelled() && ((\(releaseRun) && needs.release-publish.result == 'success') || (\(scanRun))) }}"
			"continue-on-error": true
			permissions: contents: "read"
			env: {
				GH_TOKEN:              "${{ github.token }}"
				UV_PYTHON_INSTALL_DIR: "${{ github.workspace }}/build/runtime/python"
			}
			steps: list.Concat([(githubHostSupplyAt & {checkout: githubSourceSHA, python: "3.14"}).out, [{
				name: "Scan the published runtime inventories"
				run:  "uv run --frozen python -m nox -s release_binary_scan -- --tag ${{ inputs.release_tag || inputs.scan_tag }}"
			}, {
				name: "Upload the release binary scan report"
				if:   "always()"
				uses: "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9"
				with: {
					name:                "release-binary-scan"
					path:                "build/evidence/release-binary-scan/"
					"if-no-files-found": "error"
				}
			}]])
		}
		"release-journey": {
			name:      "release journey ${{ matrix.host }}"
			"runs-on": "${{ matrix.os }}"
			needs:     "release-publish"
			if:        "${{ !cancelled() && ((\(releaseRun) && needs.release-publish.result == 'success') || (\(journeyRun))) }}"
			permissions: {
				contents:     "read"
				attestations: "read"
			}
			env: {
				GH_TOKEN:              "${{ github.token }}"
				UV_PYTHON_INSTALL_DIR: "${{ github.workspace }}/build/runtime/python"
			}
			strategy: {
				"fail-fast": false
				matrix: {
					host: [for leg in journeyLegs {leg.host}]
					include: journeyLegs
				}
			}
			steps: list.Concat([(githubHostSupplyAt & {checkout: githubSourceSHA, python: "${{ matrix.python }}"}).out, [{
				name: "Qualify the published pre-release on the adopter journey"
				env: JOURNEY_PREVIOUS: "${{ inputs.journey_previous }}"
				run: "uv run --frozen python -m nox -s release_journey -- --tag ${{ inputs.release_tag || inputs.journey_tag }} --previous \"$JOURNEY_PREVIOUS\""
			}, {
				name: "Upload the release journey receipt"
				if:   "always()"
				uses: "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9"
				with: {
					name:                "release-journey-${{ matrix.host }}"
					path:                "build/evidence/release-journey/"
					"if-no-files-found": "error"
				}
			}]])
		}
	}
}

gitlab: {
	stages: [
		"quality",
		"verify",
	]

	// Candidate integration is local-only. Hosted pipelines run only for remote-eligible
	// branches, plus merge-request validation. A new commit of a proposal ref cancels the jobs of
	// the pipeline it supersedes; no new commit cancels a dev, main or merge-request pipeline.
	workflow: {
		rules: [{
			if: "$CI_PIPELINE_SOURCE == \"merge_request_event\""
			auto_cancel: on_new_commit: "none"
		}, {
			if: "$CI_COMMIT_BRANCH == \"dev\" || $CI_COMMIT_BRANCH == \"main\""
			auto_cancel: on_new_commit: "none"
		}, {
			if: "$CI_COMMIT_BRANCH =~ /^proposal\\/.+$/"
			auto_cancel: on_new_commit: "interruptible"
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
		// The commit the bound image was built from, so a job log names the image's source.
		ETHOS_CI_SUPPLY_SOURCE: gitlabImageSource
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
		// The workflow rule of each ref decides whether a new commit cancels anything.
		interruptible: true
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
			paths: [
				"build/evidence/local-install/smoke.json",
				"build/evidence/local-install/smoke.events.jsonl",
			]
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
			// pytest-xdist's own `auto` bound: four workers through the full hosted
			// proof. The image's unprivileged user runs the entire job, preserving
			// process visibility and permission tests.
			PYTEST_XDIST_AUTO_NUM_WORKERS: "4"
		}
		script: [
			"\(offlineRun) python -m nox -s hosted_verification",
		]
		// GitHub retains raw Allure results and the Python distributions, which its release job
		// downloads; GitLab's instance artifact limit cannot hold them, so GitLab archives evidence.
		artifacts: {
			when: "always"
			paths: [
				"build/evidence/quality/proof/",
				"build/evidence/quality/tests/pytest/junit*.xml",
				"build/evidence/quality/tests/coverage/coverage.xml",
				"build/evidence/quality/security/",
				"build/evidence/quality/secrets/",
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
		variables: NODE_VERSION: _inputs.mise.tools.node
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
