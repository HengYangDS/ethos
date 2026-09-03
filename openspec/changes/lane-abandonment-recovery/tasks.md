## 1. Specify The Terminal Operation

- [x] 1.1 Validate the OpenSpec contract for preflighted, observable, resumable retirement
- [x] 1.2 Add failing tests for pure progress reduction and exact receipt validation

## 2. Make Retirement Recoverable

- [x] 2.1 Persist the immutable request before effects and derive completed/remaining effects from native observations
- [x] 2.2 Run every Git effect from the surviving control root and checkpoint each observed transition
- [x] 2.3 Expose dry-run/apply `ethos lane retire recover` with structured partial and idempotent terminal results

## 3. Route Abandonment Through The Same Owner

- [x] 3.1 Add owner-bound clean divergent abandonment derivation without restoring the retired mutation engine
- [x] 3.2 Cover worktree-removal-then-spawn-failure, recovery, repeated recovery, and foreign-holder rejection with focused and real-Git tests

## 4. Prove And Deliver

- [x] 4.1 Run focused tests, static checks, strict OpenSpec validation, and exact-HEAD proof
- [ ] 4.2 Archive, land, close out, activate the immutable package runtime, and verify package-only commands
