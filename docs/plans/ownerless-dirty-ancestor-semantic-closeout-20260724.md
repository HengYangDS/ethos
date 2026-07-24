---
subject: ethos:ownerless-dirty-ancestor-semantic-closeout-20260724
role: plan
state: active
relations:
  derives_from: all-lanes-resolution-execution-20260718
---

# Ownerless Dirty-Ancestor Semantic Closeout — 2026-07-24

Status: active target-specific authority carrier. No source effect is authorized
until this revision completes exact-HEAD proof, candidate land, and accepted-root
closeout.

Purpose: close four dirty, linked, missing-lease Work Lanes whose committed
heads are accepted ancestors without confusing preservation with semantic
absorption. Every dirty byte remains recoverable through native
`lane_resolution/preserve-retire`; the accepted Chronicles separately decide
whether the source meaning is absorbed, superseded, or explicitly rejected as
non-semantic residue.

## Exact cohort

| Branch | Head | Dirty binding | Semantic disposition | Native effect |
| --- | --- | --- | --- | --- |
| `work/adopter-legacy-root-profile-compatibility-20260720` | `b1d0cd2e0a675bf67960b37bf449ce9c158d804c` | tracked patch SHA-256 `5c0ffc8fdb626aa71f3191050f1efee6cf200b1067c6afcc6aeda29fc8e5137e`; seven untracked OpenSpec files | accepted behavior is equivalent and stricter; unique prose is distilled here | preserve-retire |
| `work/ide-ruff-runtime-adapter-20260720` | `b1d0cd2e0a675bf67960b37bf449ce9c158d804c` | one untracked 40-byte `.openspec.yaml` | explicitly rejected as incomplete bootstrap metadata with no behavior | preserve-retire |
| `work/linked-retirement-single-owner-20260720` | `66240184e924e965ff4dafa8b9cf3688b56b0a28` | tracked patch SHA-256 `6dd6465217d807c8ce7011ab2611f7001500bb3e94bf54b94a45eb94aca19955` | one-owner topology is accepted; stale half-refactor is superseded and must not be replayed | preserve-retire |
| `work/20260721-gitleaks-cache-resilience` | `ffe5bf56719a2e218d74ac1a3fd35ebe777f5136` | tracked patch SHA-256 `0b73ff784df4277ab90a70063074fe9243ad4162ed11a104dfaca52c083d20d4` | both working blobs were accepted in commit `408e06eeadae7326ada2fc4f468612971b35031a` | preserve-retire |

The observation baseline is accepted `dev` at
`266018e9832866c00499bd5bcbf4dfa9cc831d89`. The carrier proof at that baseline
passed 21 gates with evidence digest
`9864774874f523450a780ccfd56219217703fca32689e8129a5862ac99c45a49`.
A focused semantic suite covering profile migration, gitleaks persistence, and
linked/superseded retirement then passed 89 tests.

## Ordered execution

1. Accept this plan, four target-specific Claims, and four target-specific
   Chronicles through the ordinary Work Lane lifecycle.
2. Re-observe each source independently. Any head, path, dirty digest, lease,
   claim, relation-to-accepted, or occupancy drift blocks only that source.
3. Record one `preserve-retire` decision per source with break-glass, exact
   Chronicle digest, recovery plan, and explicit irreversible confirmation.
4. Run the repository-family closeout check and native dry-run before each
   effect. Native apply must first materialize and verify the preservation
   package, then remove only the bound source branch and worktree, and finally
   write its immutable receipt.
5. Verify path absence, ref absence, worktree-registration absence, package
   integrity, and resolution inventory after every source.

## Boundaries

- No valid-lease or valid-owner lane is selected.
- Preservation is rollback insurance; it is not the semantic absorption proof.
- The incomplete IDE bootstrap is rejected explicitly rather than promoted.
- No raw `git worktree remove`, branch deletion, lease deletion, recovery-package
  clear, remote push, hosted-CI claim, release, or publication is authorized.


## See Also

See also: the accepted lane-resolution authority and repository mutation/evidence rules.

- [All Work Lanes Resolution Execution](all-lanes-resolution-execution-20260718.md)
- [Ownerless First-Batch Retirement](ownerless-first-batch-retirement-20260722.md)
- [Mutation Rules](../../rules/mutation.md)
- [Evidence Rules](../../rules/evidence.md)
