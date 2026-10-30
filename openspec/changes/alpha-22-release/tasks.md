# Tasks

## 1. Release Entry

- [x] 1.1 Move the product version to 0.2.0-alpha.22 in `VERSION` and
      `distributions/npm/package.json`. Done when the lane's `ethos --version` reports
      0.2.0-alpha.22, the version tests pass unchanged and no lock changes.
      (On `60abe2f79` plus the entry, `ethos --version` reported 0.2.0-alpha.22 and the 74
      version tests passed without an edit; no lock changed.)
- [x] 1.2 Curate the `0.2.0-alpha.22` entry from the Unreleased notes, every user-visible product
      change since `v0.2.0-alpha.21` and the advisories that the release build's audit reports on
      the landed head. Done when the changelog validates with 0.2.0-alpha.22 as its release target
      (`changelog_errors` with target 0.2.0-alpha.22) and the entry names every advisory that audit
      reports.
      (On `60abe2f79` plus the entry, `changelog_errors` reported none. The audit of `ad632837e`
      reported only the six advisories in npm's bundled undici and ip-address that the entry
      names, with no unapproved finding and no Python finding; uv 0.13.6 and npm 12.2.1 were still
      the latest releases.)

## 2. Supply

- [x] 2.1 Confirm that the bound GitLab supply image still matches the release checkout. Done when
      none of the eight files that its `input.sha256` hashes differs between `c36790cd8` and the
      lane head, and the projection check passes without regenerating `.gitlab-ci.yml`.
      (`git diff c36790cd8 60abe2f79` over the eight files is empty, and `ethos lane project
      --check` reported the projections conforming.)

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` and `main` to GitHub and GitLab.
- When the landed head's hosted runs pass, the release owner creates the signed tag with
  `ethos land --release`, publishes it to both peers, dispatches the hosted release on GitHub,
  verifies the published assets, accepts the adopter path and relays the identities to the adopter
  owners.
