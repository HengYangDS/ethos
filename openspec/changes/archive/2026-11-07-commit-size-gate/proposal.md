# Proposal

## Why

The paradigm's per-file code ceiling is checked only by the whole-tree paradigm report, which runs
in `status`, readiness and the proof, never in `pre-commit`. An adopter, archpub at 0.2.0-beta.5,
committed a module that grew from 481 to 514 lexed effective lines; that commit and every later one
passed `pre-commit`, and the gap surfaced only in the full proof of the archive head, which cost an
archive, a compensation and a second proof. ETHOS hit the same class on 2026-11-07, when
re-indenting `prove` took a module from 495 to 505 lines and readiness found it after the commit.
The owner asked on 2026-11-08 to shift failures left.

## What Changes

- `pre-commit` measures each staged regular file of a registered language against the per-file code
  ceiling on its index blob, so a partial stage is judged on what is committed, and refuses with
  `pre_commit_code_size_exceeded:<path>:<lines>><ceiling>`, or `pre_commit_code_size_unmeasurable`
  for a blob it cannot read.
- The measure has one owner, shared with the paradigm report: it takes a file's language and source
  text, so each caller measures the bytes it admits.
- The paradigm report keeps its whole-tree check, so a bypassed hook still fails readiness.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: the per-file code ceiling is also admitted at commit time.

## Impact

- `src/ethos/repository/paradigm/size.py`, a new `src/ethos/adapters/repo/hook/staged_size.py`,
  `src/ethos/adapters/repo/hook/admission.py` and their tests.
- The document ceiling of the docs registry stays a readiness check; making it read index blobs
  needs the registry's generated-output and origin rules at commit time, which a later Change
  designs.
