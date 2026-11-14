## MODIFIED Requirements

### Requirement: Repository-authored names use lowercase kebab-case

Repository-authored file and directory names SHALL use lowercase kebab-case, unless an ecosystem
or tool fixes the name: module files of a language whose toolchain fixes module names, their
directories, entry documents and tool-required basenames. A name that a tracked manifest evidences
for a declared identifier source SHALL be admitted and reported; a source without evidence SHALL
be a gap. A leading `.` or `_` and dotted suffixes separate no words; immutable record roots keep
their names.

#### Scenario: A rule file uses snake_case

- **WHEN** a repository tracks `rules/module_layout.md`
- **THEN** the paradigm reports a non-standard name with its kebab-case form.

#### Scenario: An ecosystem or tool fixes the name

- **WHEN** a repository tracks `src/sample_package/module_name.py`,
  `crates/channel_solver/src/flow_graph.rs`, `.github/PULL_REQUEST_TEMPLATE.md` and
  `docs/_meta/taxonomy.toml`
- **THEN** no name is reported.

#### Scenario: A new snake_case file is requested

- **WHEN** a Work Lane requests prewrite admission for a new `rules/module_layout.md`
- **THEN** admission refuses the path and names `rules/module-layout.md`.

#### Scenario: A directory repeats a declared identifier

- **WHEN** a profile declares an identifier source with `manifests = "**/product.toml"` and
  `keys = ["product.id"]`, and a tracked `resources/Daily_Close/product.toml` declares
  `id = "Daily_Close"` under `[product]`
- **THEN** the paradigm reports no name gap for `resources/Daily_Close`
- **AND** its report lists that directory under `name_admissions` with
  `resources/Daily_Close/product.toml`.

#### Scenario: A file stem repeats a declared identifier

- **WHEN** a tracked `resources/catalog.toml` matches a declared source whose key
  `products.*.query_name` holds `used_sql`, and the repository tracks
  `resources/sql/used_sql.mysql.sql`
- **THEN** no name is reported for the file
- **AND** prewrite admits a new `resources/sql/used_sql.mssql.sql`.

#### Scenario: A value is read as its source declares

- **WHEN** one source reads `namespace = "core.a_index"` with `values = "dotted"` and another reads
  `mssql = "Shared_Sql/pre_start.mssql.sql"` with `values = "path"`
- **THEN** the names `a_index`, `Shared_Sql` and `pre_start.mssql.sql` are admitted
- **AND** with the default `values = "whole"` none of them is.

#### Scenario: An array of strings holds several identifiers

- **WHEN** a matched manifest declares `spare_queries = ["spare_sql", "probe_sql"]` under a
  declared key that is read whole
- **THEN** `resources/sql/spare_sql.mysql.sql` and `resources/sql/probe_sql.sql` are admitted, each
  by its stem.

#### Scenario: A name outside the declared identifiers is still refused

- **WHEN** the same repository tracks `resources/sql/unused_sql.mysql.sql` and no matched manifest
  names `unused_sql`
- **THEN** the paradigm reports the name with its kebab-case form.

#### Scenario: A declaration without evidence admits nothing

- **WHEN** a declared key is carried by no matched manifest, a declared glob matches no tracked
  file, or a matched manifest does not parse
- **THEN** the paradigm reports `repository_paradigm_identifier_source` with the declared key or
  the unparsable manifest
- **AND** every name that the source would evidence stays reported.
