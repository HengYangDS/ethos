# Proposal

## Why

The gap registry counts a code as registered when it has a row or begins with a family prefix. The
families exist for a code that a site assembles from parts, where no row can name every member.
The match does not ask how a code was written, so a whole literal under a broad prefix passes
without a row: a misspelled or undeclared `openspec_`, `release_` or `handoff_` code is registered
for the static test and for the shared CLI test runner alike. The review of the release diff for
0.2.0-beta.11 raised it, and a case that expects an undeclared literal under `openspec_` to be
unregistered fails on the head that this draft was written on. The Change that added the registry,
`gap-codes`, accepted this in its design as a trade-off: a new member of a family passes without a
row.

Measured on that head by three walks of the syntax tree of every module under `src/ethos` and a
reading of each value literal at its sites, kept with this draft's preparation outside this
repository:

- The table holds 1,679 code rows and 46 family rows: 35 name a code assembled from parts, and 11
  are prefixes of the artifact topology rules.
- At the positions that the static test reads (a refusal helper's gap argument, a raised error's
  first argument, a literal table read under the name `gap`), 1,540 sites carry a literal head.
  1,401 name a row, 110 are prose, and 29 are registered only through a family: 13 whole literals
  of 12 codes, 2 f-strings whose literal head holds a complete code, and 14 f-strings whose head
  is exactly a family prefix.
- For 33 of the 46 families, no site that the static test reads depends on the family.
- Over every string literal of the tree, 346 literals of 183 distinct texts begin with a family
  prefix and have no row. 41 texts are used only as field names, and 142 are used as values.
- Read at their sites, 92 of the 142 are gap codes: each reaches a raise, a refusal helper, or a
  list or a table of gaps. 12 stand at the positions that the static test reads and 80 do not; 18
  of the 80 reach a helper of the handoff package that takes the gap as its first argument. The
  other 50 are 30 names of states, roles, fields, operations, modes and notes; 9 heads, prefixes
  or parts that a site assembles into a code or tests; 8 values of a reason field that a result or
  an error carries beside its gaps; one code that a remediation hint compares and no site
  produces; and 2 parse error texts that every reader tests and none places among the gaps.
- A further 24 f-strings hold 17 complete codes, 2 of them at the positions that the static test
  reads and 15 unread, and 47 f-strings begin with 33 assembled heads.

So an exact rule at the positions that the static test reads needs 14 rows. An exact rule for a
code met at run time needs up to 109: the 92 gap codes and the 17 complete codes, each with its
owner package. That is more than a defect repair before a release holds.

## What Changes

- Every whole-literal code gets its own row, the 14 at the static positions first.
- The static test requires a row for a whole literal and for a complete code at the head of an
  f-string, and accepts a family only for an assembled head. It also reads a helper that takes the
  gap as its first argument, as the handoff package's does.
- The runner's check meets a code at run time, where the text does not show how it was built. This
  Change decides what a family then admits: a closed list of members, or a pattern that states the
  variable part.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks:
the kernel requirement `Gap codes are a registered vocabulary` states registration through a
family prefix.

## Impact

`src/ethos/contracts/codes/gaps.toml`, `src/ethos/contracts/codes/gaps.py`,
`tests/architecture/test_gap_registry.py` and the shared CLI test runner. No result and no exit
changes.

Owner: the release lead. Next action: give the 14 codes of the static positions their rows with
the static test's row rule, then the 80 other gap codes, and decide what a family admits for a
code met at run time. Read again: at the cut of 0.2.0-beta.13.
