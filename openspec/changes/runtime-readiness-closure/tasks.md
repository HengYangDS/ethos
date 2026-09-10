## 1. Bounded runtime observation

- [x] 1.1 Reproduce timeout leakage and unnecessary query import closure.
- [x] 1.2 Separate pure path projection from runtime selection; separate authority
  observation from the pure binding contract and preserve exact query diagnostics.
- [x] 1.3 Migrate callers and test non-arming timeout, fresh recovery, immutable
  launcher equality and native executable layout.

## 2. Locked package supply

- [x] 2.1 Bind identity builds to the executing locked interpreter without
  ambient build-isolation overrides.
- [x] 2.2 Pass empty-cache package tests, affected static checks and focused
  hook/runtime regressions; measure the cold query import reduction.
