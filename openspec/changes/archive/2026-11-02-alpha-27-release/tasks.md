# Tasks

## 1. Release Entry

- [x] 1.1 Move the product version to 0.2.0-alpha.27 in `VERSION` and
      `distributions/npm/package.json`. Done when the lane's `ethos --version` reports
      0.2.0-alpha.27, the version tests pass unchanged and no lock changes. (It reports
      0.2.0-alpha.27; the 686 cases that read the release carriers pass.)
- [x] 1.2 Curate the `0.2.0-alpha.27` entry from the Unreleased notes and the advisories that the
      release build's audit reports on the lane head. Done when the changelog validates with
      0.2.0-alpha.27 as its release target, the Unreleased section is empty, and the entry names
      every advisory that audit reports. (The audit decided `pass` with
      `unfixed_upstream_findings_reported` for npm 12.2.1's bundled undici, ip-address, minimatch and
      glob, whose eight advisories the `0.2.0-alpha.22` entry lists.)
- [x] 1.3 Confirm that every pinned action and supply tool is its latest stable release. Done when
      each upstream latest release, read on the lane's day, equals its pin. (Read 2026-11-02 12:53
      to 12:55: every action, uv, npm, Node, CPython and gitleaks equals its pin.)

## Workflow follow-up

- Archive this Change after `owned-literals`, prove the archived head once, then land, close out,
  bootstrap and publish `dev` and `main` to GitHub and GitLab.
- When the landed head's hosted runs pass, tag it with `ethos land --release`, publish the tag to
  both peers, dispatch the hosted release, verify the published assets, accept the adopter path on
  an upgrade from `v0.2.0-alpha.26` into `build/evidence/release/v0.2.0-alpha.27-adopter-path/`, and
  relay the identities to the adopter owners.
