# Proposal

## Why

The owner decided on 2026-11-09 that every ETHOS-governed repository has a version, while the
license grant stays a duty of published repositories. Today the paradigm judges the version source
and the changelog only when the release binding protects release tags, so an untagged repository
can carry no version at all. Of 18 governed repositories, 9 have no `VERSION`.

## What Changes

- Every governed repository keeps `VERSION` as its one version source and a Keep a Changelog
  `CHANGELOG.md`; only the tag-pattern check stays a release check.
- A missing `VERSION` whose manifest declares a version names that value in its repair, and no
  repair creates `VERSION`, since a version is the owner's claim.
- A literal `pyproject.toml` `project.version` equal to `VERSION` counts as its projection, as a
  `package.json` version does, so a backend that reads only literal metadata keeps working.
- The repair creates an absent `CHANGELOG.md` with an `[Unreleased]` section.
- `ethos form` writes `VERSION` and `CHANGELOG.md` for a new repository.
- The license grant rule is unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: governed repositories keep a version identity; released ones keep the tag
  pattern.

## Impact

- `src/ethos/repository/paradigm/report.py`, `repair.py`, the formation plan and their tests; the
  shared conforming test tree gains `VERSION` and a changelog.
- Adopters: each unversioned repository adds its version in its own Change after the release.
