## 1. Pin the unique acceptance owner

- [x] 1.1 Add a failing contract that identifies `local-install-smoke` as the
  only installability gate and proves the complete Python test target cannot
  invoke the package-acceptance effect.
- [x] 1.2 Add a failing package-owner contract for receipt observations covering
  runtime activation, immutable identity, relocation/self-repair, Work Lane
  bootstrap, and receipt-bound retirement recovery.

## 2. Migrate package-only acceptance

- [x] 2.1 Establish the delivery pipeline, runtime supply, package-acceptance
  effect, receipt, runtime, lane, and adopter-fixture owners; make the
  acceptance transaction own its sole environment, install the frozen
  production closure there once, then install the wheel without a second
  dependency resolution; update active imports and declarations, and verify the
  old module has no current consumer or compatibility facade.
- [x] 2.2 Extend the single installed-wheel run to prove hook/runtime activation,
  package-only successor materialization, runtime relocation/self-repair, and
  exact immutable identity readback; verify the new receipt observations pass.
- [x] 2.3 Extend the same installed runtime fixture to prove first-lane bootstrap
  and resumable retirement; verify no source checkout, ambient `ethos`, second
  wheel install, or second runtime build is used, and preserve the structured
  command result plus captured stderr when a lifecycle command fails.

## 3. Delete duplicate execution

- [x] 3.1 Absorb gate ordering, host-overlay, line-ending, and semantic-vector
  assertions into their existing architecture or kernel owners and verify each
  focused contract passes.
- [x] 3.2 Delete the duplicate end-to-end architecture lifecycle, its private
  helpers, the obsolete architecture file if empty, and every active reference
  to the retired owner; verify repository-wide reference closure.
- [x] 3.3 Update the quality specification and release-governance projection to
  describe one execution owner and verify strict OpenSpec plus docs checks pass.

## 4. Prove and close the atom

- [x] 4.1 Run focused delivery, architecture, runtime, lane-bootstrap, and
  retirement tests plus Ruff, types, module-layout, and source-budget gates.
- [x] 4.2 Execute the real build and `local-install-smoke` gate and verify its
  exact-HEAD receipt contains every required package-only lifecycle result.
- [x] 4.3 Freeze the final implementation candidate, verify signing readiness,
  and confirm the public lifecycle reports no pre-commit closeout gap.

## Lifecycle Transition Boundary

After every task above is complete, the implementation requires a signed commit
and exact-HEAD full proof before official archive. Archive creates a distinct
signed HEAD that then requires reproof, candidate and accepted exact CAS, fresh
immutable package-only runtime readback, and retirement of this Work Lane and
its owned temporary resources. These are mandatory terminal transitions after
the checklist, not self-referential pre-commit tasks, and MUST NOT be claimed
before their exact observations exist.
