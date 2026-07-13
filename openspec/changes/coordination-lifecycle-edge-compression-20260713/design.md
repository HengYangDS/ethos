## Context

The scoped test file measured 767 effective Python lines at base
`8022d734f14d94f438eae61a7c0b9e8236a50de6`. It already contains named tests
for distinct handoff, lease, and admission boundaries, but several assertions
are identical projections over the same pure helper contract.

## Goals / Non-Goals

**Goals:**

- Represent finite homogeneous assertion partitions as literal tables.
- Delete duplicate normalizer coverage while keeping one direct named boundary.
- Keep the file formatter-clean and reduce the formatted effective-line count.

**Non-Goals:**

- No production coordination, persistence, handoff, CLI, or JSON-contract
  change.
- No test framework or helper DSL that recreates lifecycle semantics.
- No merging of temporal SQLite/effect sequences merely for compactness.

## Decisions

1. **Use local literal tables for pure helper partitions.** The table owns only
   concrete inputs and expected public values; production functions retain all
   classification logic. This is more declarative than repeated imperative
   assertions and retains failure-local test names.
2. **Keep effectful sequences named.** Cross-host handoff failure handling,
   state-machine persistence, and ref-transaction repair use ordered effects;
   collapsing them would hide behavior rather than remove repetition.
3. **Measure after required formatting.** The quality gate formats all tracked
   Python. The raw 767-ELOC base is already formatter-clean under the canonical
   config, and the cutover must be lower than it rather than rely on layout debt.

## Risks / Trade-offs

- **Table obscures exceptional semantics** -> only uniform pure helper cases are
  tabled; effect and lifecycle tests stay named.
- **Formatter changes layout while refactoring** -> record the raw and
  formatter-clean measures; accept only a lower result under the canonical
  measure.
- **Coverage regresses during deduplication** -> retain direct normalizer input
  tuple/scalar coverage and run focused plus repository gates.

## Migration Plan

1. Commit the bounded test representation and active OpenSpec/claim carriers.
2. Validate focused tests, formatting/lint, source budget, and strict OpenSpec.
3. Archive the completed carrier, refresh generic parity from the final semantic
   head, then run HEAD-bound proof and governed promotion.
4. Restore the prior named assertions if any retained boundary loses coverage or
   diagnostic clarity.
