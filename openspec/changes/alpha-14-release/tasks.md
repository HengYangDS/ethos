# Tasks

## 1. Native Trust in Resolution

- [ ] 1.1 Ask native mise, under the caller's own trust inputs, whether the repository's configuration root is trusted. Carry only that trust to resolution's disposable copy of the exact declared bytes, for one invocation, keeping safe mode and disposable state. Done when regressions prove five things: a trusted root's copy is trusted during resolution, an untrusted root's copy is not, no trust record is written, the execution environment never carries trust, and an untrusted refusal names `mise trust`.

## 2. Windows JavaScript Reporter

- [ ] 2.1 Build the Node test-runner options in one owner and pass the reporter module as a file URL. Done when a regression proves that both callers use that owner, that the reporter is a file URL and the journal destination a file path, and that the JavaScript behavior tests pass with real Node.

## 3. Option-Safe Prose Inputs

- [ ] 3.1 Pass `--` before the Markdown inputs of codespell and Vale. Done when a regression proves that both tools check a Markdown file named like an option.

## 4. Supply Refresh

- [ ] 4.1 Move the mise floor and the CI bootstrap to 2026.10.19 with its official executable digests. Move the mise tools to Node 26.12.1, Python 3.14.9, Go 1.27.3, syft 1.55.0 and Vale 3.25.1, and relock them with `mise lock`. Done when the lock names exactly those versions and the bootstrap check accepts the bound digests.
- [ ] 4.2 Move the npm pins to OpenSpec 1.15.0, markdownlint-cli2 0.24.0, Allure 3.22.1 and the katex override 0.19.1, and refresh the npm lock natively. Done when the lock resolves only from the npm registry with integrity for every entry.
- [ ] 4.3 Refresh the Python locks with `uv lock --upgrade`, raising the moved floors and keeping Python 3.12 to 3.14. Done when both the product lock and the quality-sample lock are current.
- [ ] 4.4 Pin setup-uv v10.3.2 with uv 0.13.5, docker/login-action v4.7.0 and jdx/mise-action v5.2.3 by commit in the CI model, and regenerate the provider projections with `ethos lane project`. Done when the projection check passes.
- [ ] 4.5 Check the refreshed locks for advisories. Done when the dependency-vulnerabilities gate passes and the tests that name moved versions pass.

## 5. Release Entry

- [ ] 5.1 Move the product version to 0.2.0-alpha.14 in `VERSION`, `distributions/npm/package.json`, its `package-lock.json` entry and the three version tests. Done when the lane's `ethos --version` reports 0.2.0-alpha.14 and those tests pass.
- [ ] 5.2 Curate the `0.2.0-alpha.14` entry from the Unreleased notes, the fixes and the supply refresh above. Done when the changelog validates with 0.2.0-alpha.14 as its release target and the entry describes every product change since `v0.2.0-alpha.13`.

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, then land, close out, bootstrap and publish `dev` and `main` to GitHub.
- When the landed head's hosted runs pass on every platform, the release owner creates the signed tag with `ethos land --release`, publishes the tag, dispatches the hosted release, then verifies the published assets and relays the identities to the adopter owners.
