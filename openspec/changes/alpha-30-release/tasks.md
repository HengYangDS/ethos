# Tasks

## 1. Supply

- [x] 1.1 Move the Python locks to every release public for 24 hours at the move. Done when
      `uv lock --check` passes, the dependency declaration check reports no gap, and the moved
      packages and the cutoff are recorded here. The move ran at 2026-11-04T09:15:10Z with the
      cutoff 2026-11-03T09:15:10Z. Authlib moved from 1.9.2 to 1.9.3 and python-discovery from
      1.9.1 to 1.9.2; the quality sample's lock has neither. `uv lock --check`, ty, the
      `dependencies`, `build`, `supply_chain`, `ci_templates` and `vulnerabilities` sessions and
      877 supply tests pass.
- [x] 1.2 Bind a supply image built from moved locks. Done when no lock moved, or when the hosted
      `supply_image` workflow built the image from this lane and every GitLab supply job selects
      its digest. Run `41806635921` built and pushed it from `9f6a50e67` as `d0eef172…`.
      `lane project --check` reports the projections conforming, and the five GitLab supply jobs
      select it and none selects `ff6df8dd…`.

## 2. Release Entry

- [ ] 2.1 Move the product version to 0.2.0-alpha.30 in `VERSION` and
      `distributions/npm/package.json`. Done when the lane's `ethos --version` reports
      0.2.0-alpha.30 and the version tests pass.
- [ ] 2.2 Curate the `0.2.0-alpha.30` entry from the Unreleased notes and the advisories that the
      release build's audit reports. Done when the changelog validates with 0.2.0-alpha.30 as its
      release target, the Unreleased section is empty, and the entry names every advisory that the
      audit reports.

## Workflow follow-up

- Archive this Change after the lane's other three, prove the archived head once, then land, tag,
  release and verify. When the published artifacts pass the macOS and Linux journeys, prepare
  `0.2.0-beta.1` from the same code.
