## 1. Runtime selection contract

- [x] 1.1 Add regressions proving missing, malformed, symlinked, and invalid-target `CURRENT` selectors fail closed, while a canonical selector resolves one validated immutable runtime.
- [x] 1.2 Implement the single selector/command owner inside `adapters/repo/runtime` and verify its focused unit tests pass.

## 2. Activation and hook consumers

- [x] 2.1 Add regressions proving activation changes `CURRENT` only after runtime and hook validation, restores prior selection/config on failure, and remains idempotent.
- [x] 2.2 Replace digest-bearing launchers with selector-bound launchers; migrate runtime observation and cleanup to the selector, then prove no direct-runtime launcher parser or caller remains.

## 3. Exact public remediation

- [x] 3.1 Add regressions proving hook proof denial and runtime repair emit one absolute selected-runtime command bound to the repository root and exact HEAD without `PATH` dependency.
- [x] 3.2 Route proof and repair reports through the single runtime command owner and verify publish/pre-push projections agree.

## 4. Installed-runtime and closeout proof

- [x] 4.1 Prove an isolated wheel installs, selects, moves/reopens, and executes public status/proof-repair commands with no source checkout or ambient `ethos`.
- [ ] 4.2 Run format before lint, focused tests, type/static gates, strict OpenSpec validation, full proof and coverage; archive, land, install twice, and verify accepted runtime/hook identity plus read-only adopter diagnostics.

## Requirement To Task To Proof

| Requirement | Task | Proof |
| --- | --- | --- |
| distribution:Selected package runtime is the executable authority | 1.1 | selector failure and resolution unit regressions |
| distribution:Selected package runtime is the executable authority | 3.1 | PATH-free installed-runtime and remediation regressions |
| repository-governance:Hook runtime currentness is mutation admission | 1.2 | runtime selector focused tests |
| repository-governance:Hook runtime currentness is mutation admission | 3.2 | publish/pre-push exact command parity tests |
| repository-governance:Git-common hook runtime activation is singular | 2.1 | activation rollback and idempotence tests |
| repository-governance:Git-common hook runtime activation is singular | 2.2 | launcher/reference closure and GC tests |
| repository-governance:Git-common hook runtime activation is singular | 4.1 | isolated wheel runtime relocation smoke test |
| repository-governance:Git-common hook runtime activation is singular | 4.2 | full proof, archive, land, install, and adopter read-only evidence |
