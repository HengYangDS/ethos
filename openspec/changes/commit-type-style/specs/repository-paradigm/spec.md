## MODIFIED Requirements

### Requirement: Commits follow one grammar and carry an SSH signature

Every governed repository SHALL use the commit subject grammar of the paradigm contract: the
Conventional Commit types build, chore, ci, docs, feat, fix, perf, refactor, revert, style and
test, an optional lowercase kebab-case scope and an optional breaking marker `!`. Every commit
SHALL carry an SSH signature. `[commit_policy]` MAY restrict scopes and constrain identities; it
SHALL NOT restate the grammar or the signature.

#### Scenario: The binding declares no subject grammar

- **WHEN** `[commit_policy]` declares no `subject_pattern`
- **THEN** commit admission accepts `feat(cli)!: drop the legacy flag` and `style: reformat`, and
  rejects `spec(cli): add`.

#### Scenario: A repository declares no commit policy

- **WHEN** a repository tracks no `[commit_policy]`
- **THEN** commit admission requires the shared grammar and a trusted SSH signature on every
  introduced commit
- **AND** ETHOS signs the commits it creates.

#### Scenario: A repository adds a type

- **WHEN** a repository commit policy declares its own `subject_pattern`, for example one that
  admits a `spec` type
- **THEN** the paradigm reports a restated commit grammar.

#### Scenario: A binding restates the signature

- **WHEN** `[commit_policy]` declares `signing_required` or `signing_format`, with any value
- **THEN** the paradigm reports a restated signature declaration and the repair deletes it
- **AND** commit admission still requires an SSH signature.

#### Scenario: A scope list is declared

- **WHEN** a repository declares the scopes `cli` and `relay`
- **THEN** commit admission rejects `fix(other): repair`.
