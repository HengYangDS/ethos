# Tasks

## 1. Release Entry

- [x] 1.1 Move the `[Unreleased]` Fixed note into the `0.2.0-alpha.18` entry, date the entry
  2026-10-29 and add its Security note for uv's embedded rustls. Done when the changelog validates
  with 0.2.0-alpha.18 as its release target and `[Unreleased]` is empty (`changelog_errors` with
  target 0.2.0-alpha.18 reports none on `2c6018b27` plus the edit).

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` and `main` to GitHub and GitLab.
- When the landed head's hosted runs pass, the release owner creates the signed tag with
  `ethos land --release`, publishes it to both peers, dispatches the hosted release on GitHub,
  verifies the published assets and relays the identities to the adopter owners.
