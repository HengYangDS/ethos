## ADDED Requirements

### Requirement: Record roots have one definition

A repository's record set SHALL be its effective record roots: the paradigm's immutable roots
plus the profile's `record_roots`. Redaction, the marker verifier, the source budget and the
format repair SHALL read that set and no other. The paradigm SHALL declare its retained roots,
`docs/archive/` and `evidence/`, which with the immutable roots are never authored input and
which enter the record set only when a profile declares them. No product module SHALL restate a
retained root.

#### Scenario: A retained root is not a record root

- **WHEN** a repository tracks `evidence/decision.py` and declares no record root
- **THEN** no format selection, list rule or gate composition reads the file as authored input
- **AND** the source budget counts it as source.

#### Scenario: A declared root leaves the source budget

- **WHEN** a profile declares `record_roots = ["kept/"]` and tracks `kept/decision.py`
- **THEN** the source budget counts the file under `record_total`.

#### Scenario: The format policy still holds the retired key

- **WHEN** a format policy holds `immutable_record_roots`, whatever it names, or holds no such key
- **THEN** the source budget accepts the policy and the key decides no record.

#### Scenario: The profile is invalid

- **WHEN** the source budget measures a repository whose profile is invalid
- **THEN** it blocks with `repository_profile_invalid`.

### Requirement: The format repair keeps older declared records

A gate's verdict SHALL NOT depend on a base that one plane resolves and another does not: the
format gates and the format check SHALL judge every file under a declared record root. The format
apply SHALL NOT rewrite a declared record file that the merge base with the local accepted branch
holds unchanged, and without that base SHALL rewrite none; a named record SHALL be repaired.
Format reports SHALL name the base as `record_base`, `unresolved` without one, and the kept files
as `record_paths`.

#### Scenario: A gate judges an older record in every checkout

- **WHEN** a profile declares `docs/decisions/` and a record with trailing spaces and a loose list
  is unchanged since the accepted branch
- **THEN** the source-format gate and `ethos lane format --check` report `source_format_drift` for
  it, and the Markdown gate reports `markdown_list_spacing` for it
- **AND** they report the same in a checkout with a local accepted branch, in one that holds the
  accepted branch only as a tracking ref of `origin`, and in one that holds no such ref.

#### Scenario: The apply keeps an older record

- **WHEN** `ethos lane format --apply` runs in a Work Lane whose accepted branch holds that record
  unchanged, beside a new record and a changed one with the same faults
- **THEN** it rewrites the new and the changed record and leaves the older record's bytes
- **AND** its result names the older record under `record_paths`.

#### Scenario: The base does not resolve

- **WHEN** the checkout has no local accepted branch
- **THEN** `record_base` is `unresolved`, `record_paths` names every file under the declared root
  and the repair would rewrite none of them.

#### Scenario: A record is named

- **WHEN** a format request names `docs/decisions/old.md`
- **THEN** the repair would rewrite it, `record_base` is empty and `record_paths` is empty.

#### Scenario: A record is staged

- **WHEN** a commit stages a Markdown file under a declared record root that breaks the list rule
- **THEN** `pre-commit` refuses with `pre_commit_markdown_spacing`
- **AND** a staged file under `docs/archive/` or `evidence/` is not read.

### Requirement: A format drift refusal names its ways out

When `ethos lane format --check` refuses with `source_format_drift`, its next action SHALL name
the apply, the naming of a path under `record_paths` that rewrites a kept record, and the two Git
attributes, `linguist-vendored` and `linguist-generated`, that mark a third-party or generated
path received. The gap registry SHALL hold that text as the repair of the code.

#### Scenario: An authored file drifts

- **WHEN** `ethos lane format --check` reports `source_format_drift:docs/new.md`
- **THEN** its next action names `ethos lane format --apply`, `record_paths` and both attributes
- **AND** a check that passes names no next action.
