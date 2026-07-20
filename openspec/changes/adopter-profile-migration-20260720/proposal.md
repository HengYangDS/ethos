## Why

ETHOS tightened its typed adopter-profile declaration on July 20, 2026 without
providing a governed migration path or a JSON-safe invalid-profile boundary.
Existing adopters can therefore be structurally valid repositories whose reader
and lifecycle commands terminate with a Python traceback rather than a
machine-readable blocked verdict.

## What Changes

- Add a narrow, deterministic normalization from the former declared profile
  shape to the current profile contract; no undocumented field is silently
  preserved or guessed.
- Let an adopter name a root-level normative file as its rules authority
  without pretending that the repository root or a synthetic `rules/` tree is
  that authority.
- Make invalid adopter profiles a structured fail-closed result at public
  reader and lifecycle boundaries, never an uncaught implementation exception.
- Document the migration boundary and its non-goals.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=adopter-profile compatibility and
  fail-closed command results; reuse=extend; change=modify;
  facet:lifecycle=authoring,validation,runtime,release;
  facet:surface=cli,docs,schema,openspec;
  facet:authority=source,test,docs,openspec.

## Impact

- Affects the repository-profile parser, profile consumers, public command
  result handling, repository-governance specification, and regression tests.
- Does not change an adopter's rules, proof policy, remote configuration, or
  branch topology by itself.

## Out of Scope

- Applying the migration to DDWG or any other adopter.
- Reintroducing permissive profile parsing, a synthetic rules directory, or
  undocumented compatibility aliases.
- Landing, closeout, remote publication, hosted execution, or hosted CI
  observation.
