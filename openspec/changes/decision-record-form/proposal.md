# Proposal

## Why

The owner directed on 2026-11-18 that every governed repository's decision records follow one
strict form under the common standard, and that a record that no longer governs is kept and
marked, not removed. On 2026-11-19 he decided that the form's text lands now, since it refuses
nothing.

A census of fourteen governed repositories found 109 numbered records. Five repositories pass
the product's check of decision records and still differ in nine respects, among them the
relation that names the current owner, the place of the date, the index and what else the
directory holds. Their indexes state four different rules for a record that no longer governs.
ETHOS's own requirement says that a record is retained only while deleting it would lose a
reason; seven records were removed under it in August, and four later records replaced parts of
older ones without any mark in the older record.

## What Changes

- DR-0031 records the decision and its reasons. DR-0032, the record on branch names that the
  owner approved on 2026-11-18, lands with it in the form.
- The Docs Registry gains the section "Decision records": the exact form beside the standard it
  follows, worked examples, the life of a record, and the rule until an engine reads the four
  statuses.
- The requirement "Minimal Decision Rationale Preservation" keeps an accepted record, makes a
  changed ruling a new record and names the one form. The adopter scenario of "Singular
  Documentation Entrypoint" no longer leaves the decisions directory to each repository.
- ETHOS's own records take the first step: the date in the front matter, bodies without status
  and date lines, the relations and marks of its eight updates, and the index as one table with
  a row for each number.

Not breaking: no command, schema or check changes. A released engine accepts every byte of the
first step. The statuses other than accepted, the banners and the return of the seven removed
records follow with the engine that reads them, which the draft `decision-record-statuses`
carries.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: the two requirements named above, and one added requirement,
  "Accepted decision records are kept in one form". The rule that a record is kept and written
  in the one form stands there because the existing requirement's text would pass the
  specification's bound of 500 characters with it.

## Impact

`docs/decisions/` (every file), `docs/governance/docs-registry.md` and the `repository-governance`
specification. Every governed repository's keeper migrates through its own lane afterwards, from
this text and the first-step tool.
