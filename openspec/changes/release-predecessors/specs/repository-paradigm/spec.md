## RENAMED Requirements

- FROM: `### Requirement: The release table declares only the release mirror`
- TO: `### Requirement: The release table declares only what its readers consult`

## MODIFIED Requirements

### Requirement: The release table declares only what its readers consult

The release binding's `[release]` table SHALL declare only the keys that a reader consults,
whether or not the binding protects release tags: `mirror`, and `upgrade_from`, the releases that
a release upgrades from. The paradigm SHALL report every other key as `release-binding`, and the
repair SHALL delete such a key when it sits on a line of its own, and the table once it declares
nothing.

#### Scenario: A release table restates the version source

- **WHEN** `.ethos/release.toml` declares `[release]` with `version_source`, `tag_pattern` and
  `mirror`, and no protected release tags
- **THEN** the paradigm reports `version_source` and `tag_pattern`, and the repair deletes them and
  keeps `mirror`
- **AND** a `[release]` table left with no key is removed with the comments above it

#### Scenario: A multi-line value beside the mirror stays reported

- **WHEN** an unread `[release]` key holds a value that spans several lines beside `mirror`
- **THEN** the paradigm reports the key and the repair leaves it

#### Scenario: A release table records what the release upgrades from

- **WHEN** `.ethos/release.toml` declares `[release.upgrade_from]` and an unread key in `[release]`
- **THEN** the paradigm reports the unread key alone
- **AND** the repair deletes that key and keeps the recorded releases
