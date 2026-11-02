# Tasks

## 1. Supply

- [x] 1.1 Move every supply pin to its latest stable release through its owner's native resolver.
      Done when `uv lock --check` passes, the dependency declaration check reports no gap, every
      resolved npm URL is the public registry, the locked native supply materializes Vale 3.26.0 and
      the gates that run each moved tool pass on the moved supply. (`uv lock --check` passes; all
      555 npm lock entries resolve to the public registry; the prose gate ran the materialized Vale
      3.26.0; `prose`, `markdown_lint`, `config_quality`, `format_check`, `lint`, `dependencies`,
      `javascript_lint`, `javascript_tests`, `ci_templates`, `supply_chain` and `schemas` pass.)
- [ ] 1.2 Bind a supply image built from the moved locks. Done when the hosted `supply_image`
      workflow built and pushed it from this lane, `lane project --check` reports the projections
      conforming and every GitLab supply job selects its digest.

## 2. Release Entry

- [x] 2.1 Move the product version to 0.2.0-alpha.28 in `VERSION` and
      `distributions/npm/package.json`. Done when the lane's `ethos --version` reports
      0.2.0-alpha.28 and the version tests pass unchanged. (It reports 0.2.0-alpha.28; the 686 cases
      that read the release carriers pass.)
- [x] 2.2 Curate the `0.2.0-alpha.28` entry from the Unreleased notes and the advisories that the
      release build's audit reports on the lane head. Done when the changelog validates with
      0.2.0-alpha.28 as its release target, the Unreleased section is empty, and the entry names
      every advisory that audit reports. (The audit of the moved supply decided `pass` with
      `unfixed_upstream_findings_reported` for npm 12.2.1's bundled undici, ip-address, minimatch
      and glob, whose eight advisories the `0.2.0-alpha.22` entry lists; the Python lock reports
      none.)

## Workflow follow-up

- Archive this Change after `effect-marker-deadline`, prove the archived head once, then land, close
  out, bootstrap and publish `dev` and `main` to GitHub and GitLab.
- When the landed head's hosted runs pass, tag it with `ethos land --release`, publish the tag to
  both peers, dispatch the hosted release, verify the published assets, accept the adopter path on
  an upgrade from `v0.2.0-alpha.27` into `build/evidence/release/v0.2.0-alpha.28-adopter-path/`, and
  relay the identities to the adopter owners.
