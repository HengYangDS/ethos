## 1. Contract and RED

- [x] 1.1 Preserve the exact Hosted Windows failure showing that the inherited
  PowerShell 7 module path prevents Windows PowerShell from loading
  `Microsoft.PowerShell.Security`.
- [x] 1.2 Add focused regressions for explicit inherited-environment removal and
  for the trust-anchor adapter requesting removal of `PSModulePath`.

## 2. Unique owner repair

- [x] 2.1 Extend the existing subprocess runner with explicit environment-key
  removal and use it only at the Windows trust-anchor process boundary.
- [x] 2.2 Pass focused trust-anchor and runner tests, Ruff, format, and strict
  OpenSpec validation.

## 3. Closure

- [ ] 3.1 Freeze a signed source commit and pass exact-HEAD affected and full
  proof.
- [ ] 3.2 Archive and reprove, promote by exact CAS, activate and read back the
  immutable runtime, publish `dev` then `main` to both peers, and verify Hosted
  Windows protection across Python 3.12, 3.13, and 3.14.
- [ ] 3.3 Remove the diagnostic proposal projection and retire the Work Lane with
  no ref, worktree, Lease, or process residue.
