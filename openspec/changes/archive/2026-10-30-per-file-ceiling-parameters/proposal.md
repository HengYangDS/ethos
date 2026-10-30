# Proposal

## Why

The repository paradigm holds every governed repository to two per-file ceilings: 512 effective
lines for each tracked Python file and 512 nonblank lines for each current authored Markdown
document. A repository binding may not restate, raise or lower either. On 2026-10-31 the owner set
both ceilings to 500 for ETHOS and every governed repository, and asked that a governed repository
may use its own value, with 500 as the default.

The two earlier designs failed in opposite directions:

- Before 2026-10-15 the Python ceiling was a value in ETHOS's own `.ethos/rules.toml`. Only
  di-effect declared one, so the other governed repositories had no ceiling.
- Since then the paradigm contract fixes the value and refuses any declaration. A repository's
  difference has no outlet, and the repositories in other languages rebuilt the check with their
  own counting: aigw-cli's `tools/ci/size.go` with scc and architecture-publisher's ESLint
  `max-lines`, each pinned at 512.

A contract default that a repository may override keeps the second design's coverage and adds the
first design's flexibility. Read literally, an override would reopen both failures. A restated
value would pin the old number after the default moves. A looser value without a bound would
switch the check off. A per-file or per-role value would bring exemptions back.

## What Changes

- Both per-file ceilings default to 500, with a bound of 1000.
- A governed repository may declare its own value for either ceiling in `.ethos/rules.toml`
  `[paradigm.size]`, under the contract's key names. The value applies to every file the ceiling
  measures.
  - Without a declaration, the default applies.
  - A value equal to the default is reported as a restatement, so a later default reaches the
    repository.
  - A lower value applies.
  - A higher value applies when it is within the bound and `[paradigm.size.reasons]` states why;
    the paradigm report lists it as a deviation from the default.
  - A higher value without a reason, a value above the bound, a non-positive value or an unknown
    key is reported, and the default applies.
- The paradigm report and docs health judge each file against the repository's effective ceiling.
  The measures do not change.
- The retired `[quality.code_size]` table is still reported, now with the repair to declare
  `[paradigm.size]`.
- ETHOS brings its 13 Python files above 500 effective lines within the default: twelve split by
  semantic ownership, and `adapters/repo/git.py` through `retire-unreachable-product-code`, which
  removes code that nothing calls.
- **BREAKING** for governed repositories: after they rebind, 17 Python files and 10 Markdown
  documents in five repositories exceed the default (the preview is in the design).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: the Python size ceiling becomes a contract default with a bounded
  repository value.
- `quality`: the Markdown ceiling becomes the same kind of value.

## Impact

- `src/ethos/contracts/paradigm/paradigm.toml` and `declaration.py`: the default and the bound.
- `src/ethos/repository/paradigm/`: one owner resolves the effective ceilings and reports
  declarations; the paradigm report and docs health read it.
- 13 ETHOS Python files across `src/`, `tests/` and `tools/` brought within 500, with their tests.
- Out of scope: measuring other languages (Go, JavaScript, TypeScript). That belongs to the
  shared-ownership design's sink of business-free checks into the base, with its own fleet preview.
  The design records the instrument comparison that sink starts from.
