# Proposal

## Why

A defect admitted to the beta.11 batch on 2026-11-14, because it blocks one adopter's bind. ETHOS
has one notion of a received path: a path that Git attributes mark `linguist-vendored` or
`linguist-generated` is received rather than authored. The commit hook's text check, the name rule,
the code ceiling and the authored-text validation leave such a path alone. The format selection does
not: `prepare_source_format` and `source_format_report` (`src/ethos/adapters/gates/formatting.py`)
select through `authored_source_files` (`src/ethos/adapters/gates/native/inputs.py`), which
subtracts producer, upstream, archived-record and dependency owners but not received paths. So
`ethos lane format --check` and the source-format gate report `source_format_drift` for an upstream
license in a vendored tree, and `--apply` rewrites it. The repository can pass only by rewriting a
third party's text or by leaving the gate. The Markdown, prose, link and configuration gates read
the same join and judge the same bytes, whose layout `pre-commit` admits.

## What Changes

- `authored_source_files`, the one join of authored inputs, subtracts the paths that Git attributes
  mark vendored or generated. `ethos lane format` in its preview, check and apply forms, the
  source-format gate and the Markdown, prose, link and configuration gates no longer select them.
- A format request that names a received path refuses `source_format_other_owner:<path>`, as it does
  for an archived record or a generated projection; a configuration request refuses it as a target
  with another owner.
- `authored_text_files` no longer subtracts received paths a second time; it reads the join's
  output.
- The Unreleased section of `CHANGELOG.md` gains a Fixed line.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: adds `Received paths are not authored inputs`.

## Impact

`src/ethos/adapters/gates/native/inputs.py`, `tests/unit/adapters/gates/test_source_format.py`,
`tests/unit/adapters/gates/test_prose.py` and `CHANGELOG.md`. No command, flag, gap code or result
schema changes. Out of scope: byte-bound carriers, which format selection already leaves alone and
which the read-only checks still read; and the staged size check and prewrite path admission, which
subtract Git attributes without those carriers.
