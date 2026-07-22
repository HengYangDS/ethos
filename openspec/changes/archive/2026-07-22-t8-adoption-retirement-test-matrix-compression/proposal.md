# T8 Adoption-Retirement Test-Matrix Compression

## Why

The adoption-retirement suite repeats repository setup, parity/shadow envelopes,
manifest mutations, and assertion shapes across finite failure partitions. At
the current HEAD, `scc --dryness` reports 401 repeated code lines in the primary
731-code-line test module, making it the repository's largest isolated DRY
opportunity outside active foreign Work Lanes.

## What Changes

- Replace equivalent setup and assertion bodies with literal, domain-named
  pytest case tables and inert test fixture builders.
- Keep expected retirement states, gaps, checks, and actions literal rather
  than deriving them from production classification.
- Preserve distinct tests for Git effects, CLI execution, rollback evidence,
  and state-transition boundaries.
- Delete every superseded test body and require a formatter-clean net reduction
  in scoped test ELOC and `scc` duplicate lines.

## Out Of Scope

- Product retirement behavior, public JSON, profile schema, or rollback policy.
- Source-budget v2 measurement work owned by another active Work Lane.
- Foreign Work Lane integration, retirement, remote publication, or hosted CI.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: subject=adoption-retirement-test-matrix-compression; reuse=extend;
  change=modify; facet:lifecycle=validation; facet:surface=test,openspec,evidence;
  facet:authority=source,test,openspec,claim,evidence.

## Impact

The bounded implementation may change
`tests/unit/adoption/test_retirement.py` and its existing fixture module. It adds
no product dependency, compatibility path, wrapper, generated test source, or
parallel retirement implementation.
