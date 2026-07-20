## 1. Campaign bootstrap

- [x] 1.1 Create the dedicated strict-serial campaign manifest with the active bootstrap step and independent planned successor steps.
- [x] 1.2 Bind the active OpenSpec carrier, Claim, Chronicle, scope companion, and campaign metadata.

## 2. Scoped local closeout

- [x] 2.1 Add explicit `--campaign` selection to the read-only campaign closeout command and report.
- [x] 2.2 Add focused regressions and command documentation for scoped closeout.

## 3. Verification and handoff

- [x] 3.1 Refresh the Chronicle digest after final implementation evidence and mark the Claim’s final evidence binding.
- [x] 3.2 Run focused tests and strict OpenSpec/lifecycle/claim validation; record the committed pre-archive proof state, then rerun after the official archive before candidate land.
- [x] 3.3 Record only the measured bootstrap TOML growth as expiring source-budget debt and refresh the directly stale lifecycle Claim scope.

The archive, candidate land, accepted-root closeout, owned-lane retirement, and campaign-step update are post-archive lifecycle transitions. They are governed outside this carrier checklist and are not asserted complete until their respective transitions have occurred.
