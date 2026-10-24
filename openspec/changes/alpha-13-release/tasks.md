# Tasks

## 1. Release Entry

- [ ] 1.1 Move the product version to 0.2.0-alpha.13 in `VERSION`, `distributions/npm/package.json`, its `package-lock.json` entry and the three version tests; done when the lane's `ethos --version` reports 0.2.0-alpha.13 and those version tests pass.
- [ ] 1.2 Curate the `0.2.0-alpha.13` entry from the Unreleased notes and the mise fix; done when the changelog validates with 0.2.0-alpha.13 as its release target and the entry describes every product change since `v0.2.0-alpha.12`.

## 2. Verify

- [ ] 2.1 Run strict OpenSpec validation and the Markdown checks; verify that only the release-entry files and this Change changed.

## Workflow follow-up

- Prove the exact head, archive this Change, prove the archived head, then land, close out, bootstrap and publish `dev` and `main` to GitHub.
- When the landed head's hosted runs pass on every platform and the release build's dependency audit is clean on it, create the signed tag with `ethos land --release`, publish the tag to GitHub and dispatch the hosted release.
- Verify the published assets along the adopter path, upgrading from alpha.12, then give the tag, wheel and runtime digests to the adopter owners.
