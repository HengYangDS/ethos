## ADDED Requirements

### Requirement: The release table declares only the release mirror

The release binding's `[release]` table SHALL declare only `mirror`, the one key its reader
consults, whether or not the binding protects release tags. The paradigm SHALL report every other
key as `release-binding`, and the repair SHALL delete such a key when it sits on a line of its own,
and the table once it declares nothing.

#### Scenario: A release table restates the version source

- **WHEN** `.ethos/release.toml` declares `[release]` with `version_source`, `tag_pattern` and
  `mirror`, and no protected release tags
- **THEN** the paradigm reports `version_source` and `tag_pattern`, and the repair deletes them and
  keeps `mirror`
- **AND** a `[release]` table left with no key is removed with the comments above it

#### Scenario: A multi-line value stays reported

- **WHEN** an unread `[release]` key holds a value that spans several lines
- **THEN** the paradigm reports the key and the repair leaves it
