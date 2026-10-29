# Tasks

## 1. Release Entry

- [x] 1.1 Add the npm bundled-package note to the `0.2.0-alpha.19` Security section of
  `CHANGELOG.md`. Done when the changelog validates with 0.2.0-alpha.19 as its release target
  (`changelog_errors` with target 0.2.0-alpha.19) and the note names the six advisories that the
  release audit on `0ba9a7e44` reported as unfixed upstream.
  (On `0ba9a7e44` plus the note, `changelog_errors` reported none; the note names all six.)

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` and `main` to GitHub and GitLab.
- When the landed head's hosted runs pass, the release owner creates the signed tag with
  `ethos land --release`, publishes it to both peers, dispatches the hosted release on GitHub,
  verifies the published assets and relays the identities to the adopter owners.
