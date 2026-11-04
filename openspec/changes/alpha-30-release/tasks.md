# Tasks

## 1. Supply

- [ ] 1.1 Move the Python locks to every release public for 24 hours at the move. Done when
      `uv lock --check` passes, the dependency declaration check reports no gap, and the moved
      packages and the cutoff are recorded here.
- [ ] 1.2 Bind a supply image built from moved locks. Done when no lock moved, or when the hosted
      `supply_image` workflow built the image from this lane and every GitLab supply job selects
      its digest.

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
