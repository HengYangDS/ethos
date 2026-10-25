# Tasks

## 1. Admit retained upgrade inputs

- [x] 1.1 Reuse native runtime scope admission before package setup; regress foreign private refusal
      and valid external supply without changing either destination.
- [x] 1.2 Separate activation coordination from explicit runtime selection; verify manifest-bound
      predecessor rollback, accepted self-hosted authority and nonmutating supply refusal.
      Evidence: `build/evidence/local-install/manifest-selection-smoke.json` (`cec5d6c6c`).

## 2. Migrate retained authoring identities

- [x] 2.1 Implement the native owned-topic migration; verify fresh ref admission and preserved dirty
      bytes, index intent, Lease holder and recoverable projection failure.
      Evidence: `build/evidence/retained-runtime-preservation/focused/topic-binding-work-green.xml`.
- [x] 2.2 Qualify active Change migration through prewrite and native signed commits; verify
      preserved task identities, unrelated index intent and exact collision refusal.
      Evidence: `build/evidence/local-install/attempts/27f575058-retained-qualified/smoke.json`.

## 3. Qualify the retained consumer

- [x] 3.1 Pass installed predecessor upgrade, rollback and renewed authoring with nonempty retained
      state and legacy identities through public native commands.
      Evidence: `build/evidence/local-install/attempts/27f575058-retained-qualified/smoke.json`.
- [ ] 3.2 Qualify the final source within the native source budget, with focused quality and review,
      strict OpenSpec validation and official archive simulation.
      Current dependency: `build/evidence/retained-runtime-preservation/focused/source-budget-after-native-simplification.json`.

## Workflow follow-up

- Obtain exact-current proof before archive and integration on the released alpha.14 baseline.
- Adopter cutover and retirement require their own current admission and consumer acceptance.
