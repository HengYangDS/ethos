# Tasks

## 1. Native Trust in Resolution

- [x] 1.1 Ask native mise, under the caller's own trust inputs, whether the repository's configuration root is trusted. Carry only that trust to resolution's disposable copy of the exact declared bytes, for one invocation, keeping safe mode and disposable state. Done when regressions prove five things: a trusted root's copy is trusted during resolution, an untrusted root's copy is not, no trust record is written, the execution environment never carries trust, and an untrusted refusal names `mise trust` (`test_resolution_carries_only_native_trust_to_its_copy`, `test_native_supply_resolution_leaves_no_host_mise_state`).
- [x] 1.2 Carry the same native trust to provisioning's disposable copy. Done when a regression proves that provisioning from a trusted root passes the trust to its copy and provisioning from an untrusted root passes none (`test_provisioning_carries_only_native_trust_to_its_copy`).

## 2. Windows JavaScript Reporter

- [x] 2.1 Build the Node test-runner options in one owner and pass the reporter module as a file URL. Done when a regression proves that both callers use that owner, that the reporter is a file URL and the journal destination a file path, and that the JavaScript behavior tests pass with real Node (`test_node_test_options_name_the_reporter_module_by_file_url`, `test_behavior_gate_gives_node_the_one_owned_test_options`; real Node: `tests/unit/adoption/quality/test_evidence.py`).

## 3. Option-Safe Prose Inputs

- [x] 3.1 Pass `--` before the Markdown inputs of codespell and Vale. Done when a regression proves that both tools check a Markdown file named like an option (`test_prose_tools_read_a_document_named_like_an_option`).

## 4. Supply Refresh

- [x] 4.1 Move the mise floor and the CI bootstrap to 2026.10.19 with its official executable digests. Move the mise tools to Node 26.12.1, Python 3.14.9, Go 1.27.3, Syft 1.55.0 and Vale 3.25.1, and relock them with `mise lock`. Done when the lock names exactly those versions and the bootstrap check accepts the bound digests (`ci_templates`; the official macos-arm64 binary matches its bound digest).
- [x] 4.2 Move the npm pins to OpenSpec 1.15.0, markdownlint-cli2 0.24.0, Allure 3.22.1 and the katex override 0.19.1, and refresh the npm lock natively. Done when the lock resolves only from the npm registry with integrity for every entry (`dependencies`; the npm audit equals the baseline).
- [x] 4.3 Refresh the Python locks with `uv lock --upgrade`, raising the moved floors and keeping Python 3.12 to 3.14. Done when both the product lock and the quality-sample lock are current (`uv lock --upgrade` for both locks).
- [x] 4.4 Pin setup-uv v10.3.2 with uv 0.13.5, docker/login-action v4.7.0 and jdx/mise-action v5.2.3 by commit in the CI model, and regenerate the provider projections with `ethos lane project`. Done when the projection check passes (`ethos lane project --apply`, `ci_templates`).
- [x] 4.5 Check the refreshed locks for advisories. Done when the dependency-vulnerabilities gate passes and the tests that name moved versions pass (`vulnerabilities`, full `tests`).

## 5. Release Entry

- [x] 5.1 Move the product version to 0.2.0-alpha.14 in `VERSION`, `distributions/npm/package.json`, its `package-lock.json` entry and the three version tests. Done when the lane's `ethos --version` reports 0.2.0-alpha.14 and those tests pass (`tests/unit/cli/test_version_command.py`, `tests/unit/release/test_version_identity.py`).
- [x] 5.2 Curate the `0.2.0-alpha.14` entry from the Unreleased notes, the fixes and the supply refresh above. Done when the changelog validates with 0.2.0-alpha.14 as its release target and the entry describes every product change since `v0.2.0-alpha.13` (`changelog_errors` with target 0.2.0-alpha.14).

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, then land, close out, bootstrap and publish `dev` and `main` to GitHub.
- When the landed head's hosted runs pass on every platform, the release owner creates the signed tag with `ethos land --release`, publishes the tag, dispatches the hosted release, then verifies the published assets and relays the identities to the adopter owners.
