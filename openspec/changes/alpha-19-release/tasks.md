# Tasks

## 1. Release Entry

- [ ] 1.1 Move the product version to 0.2.0-alpha.19 in `VERSION`, `distributions/npm/package.json`, its `package-lock.json` and the three version tests. Done when the lane's `ethos --version` reports 0.2.0-alpha.19 and those tests pass (`tests/unit/cli/test_version_command.py`, `tests/unit/release/test_version_identity.py`, `tests/unit/release/test_policy_attestation.py`).
- [ ] 1.2 Curate the `0.2.0-alpha.19` entry from the Unreleased notes and every user-visible product change since `v0.2.0-alpha.18`. Done when the changelog validates with 0.2.0-alpha.19 as its release target and the entry describes every user-visible product change since `v0.2.0-alpha.18` (`changelog_errors` with target 0.2.0-alpha.19).

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish `dev` and `main` to GitHub and GitLab.
- When the landed head's hosted runs pass, the release owner creates the signed tag with `ethos land --release`, publishes it to both peers, dispatches the hosted release on GitHub, verifies the published assets and relays the identities to the adopter owners.
