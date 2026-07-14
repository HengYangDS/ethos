## Why

A valid adopter can currently pass `ethos plan` or `ethos prove` because both
commands skip the official OpenSpec lifecycle outside the product root.

## What Changes

- Run `openspec_governance_report(..., lifecycle=True)` for every governed root.
- Surface lifecycle gaps directly; do not add them to code-correctness gates.
- Keep OpenSpec as the only Change carrier; method packages are non-authoritative.

## Impact

- `packages/ethos/src/ethos/surface/cli/root/{planning,proof}.py`
- CLI contract regression and repository-governance specification.

## Out Of Scope

Material-path-to-Change scope admission is recorded in
`adopter-material-change-scope-20260714`; it is not implemented by this Change.

## Capabilities

- `repository-governance`: subject=adopter-change-lifecycle; reuse=extend;
  change=modify; facet:lifecycle=validation; facet:surface=cli,test,docs;
  facet:authority=source,test,openspec,claim,evidence

## Out Of Scope

Material-path scope admission, official schema changes, code-correctness gate
changes, and method-package authority.
