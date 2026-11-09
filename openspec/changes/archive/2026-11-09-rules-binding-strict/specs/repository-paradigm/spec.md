## ADDED Requirements

### Requirement: The rules binding declares only the tables its readers consult

`rules.toml` SHALL declare only `[paradigm]`, `[profiles]` and `[[rule]]`, apart from an
`[artifacts]` table that retires into the profile's `record_roots` and a `[quality]` table whose
`code_size` becomes a `[paradigm.size]` value. The paradigm SHALL report every other top-level key
as `rules-binding`, and the repair SHALL delete such a table, or the binding once it declares
nothing, and SHALL leave a bare value reported.

#### Scenario: A rules binding declares a table no reader consults

- **WHEN** `.ethos/rules.toml` declares `[formats]` or `[gates]`
- **THEN** the paradigm reports the table and the repair deletes it
- **AND** a rules binding left with no table is deleted

#### Scenario: A rules table with its own move is kept

- **WHEN** `.ethos/rules.toml` declares `[artifacts]`, or a `[quality]` table that holds
  `code_size`, alone or beside another key
- **THEN** the paradigm reports neither as `rules-binding`, and the repair deletes neither

#### Scenario: A bare value stays reported

- **WHEN** `.ethos/rules.toml` declares a top-level key that is not a table, such as
  `formats = "TOML"`
- **THEN** the paradigm reports it as `rules-binding` and the repair leaves it
