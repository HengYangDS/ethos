package ci

import "strings"

// Repository CUE instantiates the contract; native parameters bind its selected supply.
#Verification: {
	parameters: {
		name:            string & !=""
		accepted_branch: string & =~"^[a-z][a-z0-9-]*$"
		release_branch:  string & =~"^[a-z][a-z0-9-]*$"
		report_path:     *"build/evidence/ci/verification.json" | string & =~"^build/evidence/ci/[a-z0-9-]+[.]json$"
		timeout_minutes: int & >=1 & <=120
		evidence_paths: *[] | [...string & =~"^build/evidence/[a-zA-Z0-9][a-zA-Z0-9._/-]*$" & !~"(^|/)[.][.](/|$)"]
		supply: {
			mise_version: string & =~"^[0-9]{4}[.][0-9]+[.][0-9]+$"
			checks: {
				github: *[] | [...string & !=""]
				gitlab: *[] | [...string & !=""]
			}
		}
		github?: runners: [string, ...string]
		gitlab?: {
			offline_candidate_variable: *"ETHOS_OFFLINE_CANDIDATE" | string & =~"^[A-Za-z_][A-Za-z0-9_]*$"
			stages: *["verify"] | ["verify", ...string]
			variables: *{} | {[Name=string & =~"^[A-Za-z_][A-Za-z0-9_]*$"]: string}
			runners: [Name=string]: {
				system: "linux" | "macos" | "windows"
				review_tags: [string, ...string]
				protected_tags: [string, ...string]
				image?:          string & =~"@sha256:[0-9a-f]{64}$"
				resource_group?: string & !=""
				preparation: *[] | [...string & !=""]
				variables: *{} | {[Name=string & =~"^[A-Za-z_][A-Za-z0-9_]*$"]: string}
			}
		}
	}
	let policy = parameters
	let sourceHead = "${{ github.event.pull_request.head.sha || github.sha }}"
	let evidence = [policy.report_path, for path in policy.evidence_paths {path}]
	let invocation = "mise exec --locked -- ethos prove --host --execute --full --json > \(policy.report_path)"
	let offlineCandidate = "$\(policy.gitlab.offline_candidate_variable)"
	let sourceRules = [{if: offlineCandidate, when: "never"}, {
		if: "$CI_COMMIT_REF_PROTECTED == \"true\" && ($CI_COMMIT_BRANCH == \"\(policy.accepted_branch)\" || $CI_COMMIT_BRANCH == \"\(policy.release_branch)\" || $CI_COMMIT_TAG =~ /^v[^\\/]*$/)"
	}]
	let reviewRules = [{if: offlineCandidate, when: "never"}, {
		if: "$CI_PIPELINE_SOURCE == \"merge_request_event\" || ($CI_COMMIT_BRANCH =~ /^proposal\\// && $CI_PIPELINE_SOURCE == \"push\")"
	}]
	let githubJob = {
		"runs-on":         "${{ matrix.os }}"
		"timeout-minutes": int
		strategy: {"fail-fast": false, matrix: os: policy.github.runners}
		steps: [{
			uses: "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
			with: {
				"fetch-depth": 0
				ref:           sourceHead
			}
		}, {
			uses: "jdx/mise-action@6be3c7ed4c21d4f76b208d351d95aac273ebb76d"
			with: {version: policy.supply.mise_version, install: false, cache: false}
		}, {name: "Acquire locked product supply", run: "mise install --locked --jobs=1"},
			for command in policy.supply.checks.github {{name: "Check locked supply", run: command}}, {
				name:  "Prepare owned evidence directory"
				shell: "bash"
				run:   "mkdir -p build/evidence/ci"
			}, {
				name:  "Execute installed verification"
				run:   invocation
				shell: "bash"
			}, {
				uses: "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9"
				if:   "always()"
				with: {
					name:                "verification-${{ matrix.os }}"
					path:                strings.Join(evidence, "\n")
					"if-no-files-found": "error"
				}
			}]
	}
	providers: {
		if policy.github != _|_ {
			github: {
				name: policy.name
				on: {
					push: {branches: [policy.accepted_branch, policy.release_branch, "proposal/**"], tags: ["v*"]}
					pull_request: branches: [policy.accepted_branch, policy.release_branch]
					workflow_dispatch: {}
				}
				permissions: contents: "read"
				jobs: {
					[Name=string]: _
					verify: githubJob & {"timeout-minutes": policy.timeout_minutes}
				}
			}
		}
		if policy.gitlab != _|_ {
			gitlab: {
				[Name=string]: _
				workflow: rules: [{
					if: "\(offlineCandidate) && $CI_COMMIT_REF_PROTECTED == \"true\" && ($CI_COMMIT_BRANCH == \"\(policy.accepted_branch)\" || $CI_COMMIT_BRANCH == \"\(policy.release_branch)\") && ($CI_PIPELINE_SOURCE == \"api\" || $CI_PIPELINE_SOURCE == \"web\")"
				}, {if: offlineCandidate, when: "never"}, {if: "$CI_PIPELINE_SOURCE == \"merge_request_event\""}, {
					if: "$CI_COMMIT_BRANCH =~ /^proposal\\// && $CI_OPEN_MERGE_REQUESTS", when: "never"
				}, {if: "$CI_COMMIT_BRANCH == \"\(policy.accepted_branch)\" || $CI_COMMIT_BRANCH == \"\(policy.release_branch)\" || $CI_COMMIT_BRANCH =~ /^proposal\\// || $CI_COMMIT_TAG =~ /^v[^\\/]*$/"}]
				stages: policy.gitlab.stages
				for name, runner in policy.gitlab.runners {
					for trust, selectedTags in {review: runner.review_tags, protected: runner.protected_tags} {
						"verify:\(name):\(trust)": {
							stage:         "verify"
							tags:          selectedTags
							timeout:       "\(policy.timeout_minutes) minutes"
							interruptible: true
							variables: {GIT_DEPTH: "0"} & policy.gitlab.variables & runner.variables
							if runner.image != _|_ {image: runner.image}
							if runner.resource_group != _|_ {resource_group: runner.resource_group}
							if trust == "review" {rules: reviewRules}
							if trust == "protected" {rules: sourceRules}
							if runner.system != "windows" {before_script: [
								for command in runner.preparation {command},
								"mise install --locked --jobs=1",
								for command in policy.supply.checks.gitlab {command},
								"mkdir -p build/evidence/ci",
							]}
							if runner.system == "windows" {
								before_script: [
									for command in runner.preparation {command},
									"mise install --locked --jobs=1",
									for command in policy.supply.checks.gitlab {command},
									"New-Item -ItemType Directory -Force build/evidence/ci",
								]
							}
							script: [invocation]
							artifacts: {when: "always", paths: evidence}
						}
					}
				}
			}
		}
	}
}
