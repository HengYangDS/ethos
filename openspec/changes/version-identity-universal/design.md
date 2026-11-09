# Design

## Context

`_release_gaps` returns unless the release binding protects tags, and then checks the tag pattern,
the presence of `VERSION`, a `pyproject.toml` `[project] version`, a `package.json` version that
differs from `VERSION` and the changelog grammar. `license_gaps` requires a grant when the
repository tags releases or a manifest declares a license. `CarrierEdit` can create an absent
carrier, and `ethos form` writes the starter files before its first paradigm check.

## Goals / Non-Goals

Goals: a version identity in every governed repository, without choosing a version for its owner.

Non-Goals: the license rule; sub-package versions of a workspace, which stay their manifests'; an
archived-repository exemption, which no lifecycle state supports today.

## Decisions

1. **Only the tag check is a release check.** `_release_gaps` checks the tag pattern when tags are
   declared, and the version and changelog checks for every governed repository.
2. **No repair chooses a version.** Without `VERSION`, one gap `version-source:VERSION` is reported;
   when a manifest declares a version, its repair names that value, and the manifest is not also
   reported as a second source. A manifest version beside an existing `VERSION` that differs from
   it stays a second source.
3. **The changelog is seeded only when absent.** A `changelog` repair creates `CHANGELOG.md` with
   `# Changelog` and `## [Unreleased]`; an existing changelog with errors stays reported.
4. **Formation writes both files.** `ethos form` writes `VERSION` (`0.1.0-alpha.0`, ending with a
   newline) and the changelog before its paradigm check, so a formed repository reports no gap.

## Risks / Trade-offs

- Each unversioned repository turns red after it upgrades, until its owner adds `VERSION`; the
  repair names the manifest's version where one exists.
