# Tasks

## 1. Release Entry

- [x] 1.1 Move the product version to 0.2.0-alpha.26 in `VERSION` and
      `distributions/npm/package.json`. Done when the lane's `ethos --version` reports
      0.2.0-alpha.26, the version tests pass unchanged and no lock changes. (It reports
      0.2.0-alpha.26; the 801 cases that read the release carriers pass.)
- [x] 1.2 Curate the `0.2.0-alpha.26` entry from the Unreleased notes and the advisories that the
      release build's audit reports on the lane head. Done when the changelog validates with
      0.2.0-alpha.26 as its release target, the Unreleased section is empty, and the entry names
      every advisory that audit reports. (The audit decided `pass` with
      `unfixed_upstream_findings_reported` for the eight npm 12.2.1 bundle advisories that the
      `0.2.0-alpha.22` entry lists.)
- [x] 1.3 Select `jdx/mise-action` 5.2.5 in the shipped adopter CI model. Done when the CI template
      and projection checks pass with the new pin. (`ci_templates`, `config_quality` and
      `ethos lane project --check` pass.)

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` and `main` to GitHub and GitLab.
- When the landed head's hosted runs pass, tag it with `ethos land --release`, publish the tag to
  both peers, dispatch the hosted release, verify the published assets, accept the adopter path and
  relay the identities to the adopter owners.
