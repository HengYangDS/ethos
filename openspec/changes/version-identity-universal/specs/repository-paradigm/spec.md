## ADDED Requirements

### Requirement: Governed repositories keep a version identity

Every governed repository SHALL keep `VERSION` as its only version source and `CHANGELOG.md` in
Keep a Changelog 1.1.0 with an `[Unreleased]` section and bracketed version headings. A root
`package.json` `version` equal to `VERSION` SHALL count as its projection. No repair SHALL choose
a version; the license grant SHALL stay a duty of released repositories.

#### Scenario: A second version source exists

- **WHEN** a governed repository keeps a literal version in `package.json` that differs from
  `VERSION`
- **THEN** the paradigm reports two version sources.

#### Scenario: The npm manifest projects VERSION

- **WHEN** a governed repository's root `package.json` declares the version that `VERSION` holds
- **THEN** the paradigm reports no version-source gap
- **AND** the same manifest without `VERSION` reports the missing source once, naming its version.

#### Scenario: A version heading is unbracketed

- **WHEN** `CHANGELOG.md` contains `## 1.2.0 - 2026-10-14`
- **THEN** the paradigm reports a non-standard version heading.

#### Scenario: An untagged repository has no version

- **WHEN** a governed repository declares no release tags and tracks no `VERSION`
- **THEN** the paradigm reports the missing version source
- **AND** it reports no license gap for a missing `LICENSE`

### Requirement: Released products tag their version

A repository that publishes releases SHALL protect release tags as `v` followed by a Semantic
Versioning version, and each tag SHALL name the `VERSION` that its version identity keeps.

#### Scenario: A release tag pattern differs

- **WHEN** the release binding protects tags other than `v*`
- **THEN** the paradigm reports the release tag pattern

## REMOVED Requirements

### Requirement: Released products keep one version source

**Reason**: Its version source, manifest projection and changelog rules now apply to every
governed repository, and its tag rule to released ones.

**Migration**: Use "Governed repositories keep a version identity", which carries its three
scenarios, and "Released products tag their version".
