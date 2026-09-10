## Context

See the proposal for the observed disagreement. The product contract and
quality specification already require one owner per property and one declared
proof graph. The implementation still keeps separate lists in local CI and a
second executor, so adding another tool would increase ambiguity rather than
assurance. Complete-system coverage is assessed in the existing terminal plan;
this Change repairs the execution boundary on which that coverage depends.

## Goals / Non-Goals

Make every selected obligation discoverable through one native declaration,
execute its dependency closure once, and distinguish failed, unknown and
unexecuted observations. Preserve existing checks and their actual costs without
claiming that selection alone closes their individual quality defects.
Do not make live network services prerequisites for local-only correctness,
create a parallel scheduler, restore retired tool catalogs, or weaken coverage
and independent product/test budgets.

## Decisions

### One graph, distinct evidence planes

The existing gate declaration owns check identity, dependencies and selection.
Native tool configuration owns its effective policy and lock identity. Local CI
selects from that declaration and invokes the existing runner, rather than
maintaining session arrays or calling another scheduler through nested Nox.
Offline source correctness, current external dependency/security knowledge,
package conformance and hosted observations retain explicit boundaries. An
unavailable required observation is unknown or blocked, never a passing empty
report. Hosted observation is explicitly requested after publication and does
not poll its own in-flight pipeline inside local verification.

Default selects offline source checks. Full verification and local CI select the
same wider declared closure, whose security freshness and provisioning adapters
may require network access. Neither profile proves hosted success. This reuses
the two existing proof sets rather than adding a new profile registry.

### Dependency outcomes control execution

The shared runner retains deterministic, bounded waves and isolates writers.
A node executes only after each prerequisite has actually passed with a zero
exit code. Dry-run results stay unknown; they are projections, not failed runs. Failed or
unknown predecessors yield an unexecuted blocked result identifying their IDs;
independent diagnostics may continue. Coverage failure therefore cannot launch
package creation merely because the graph is topologically sorted.

### Preserve effective checks, delete parallel authority

Compare the existing local and full-proof closures before replacing them.
Register missing existing native owners without copying their implementation.
Delete redundant selection/scheduling state and nested aggregate calls. Retain
only a thin local execution/evidence transport. A HEAD-bound fallback requires
clean committed source and starts with a non-passing receipt before checks run.
Interrupted, missing, duplicated or command-mismatched execution cannot pass.
One exact source/policy binding
and every required result determine success. Native formatting, linting, typing,
structural checks, tests, security, packaging and operational/resource assurance
remain separate properties, not separate control planes.

## Risks / Trade-offs

- Broad full-proof membership can introduce network dependence. Classify each
  owner before admitting it to an offline or online evidence plane.
- Tool metadata and old research are not implementation evidence. Existing
  scope omissions, stale registries and false-green checks remain explicit gaps.
- New failure propagation changes diagnostics. Test the public outcomes and
  preserve stderr and the exact unmet dependency rather than error-string shims.
- More coverage can increase runtime. Remove duplicate execution, reuse bounded
  scheduling and measure actual cost without reducing mandatory assurance.

## Migration Plan

First reproduce divergence and unsafe downstream execution with focused tests.
Replace local selection and scheduling with the existing owner, migrate every
necessary check to its proper plane, and remove the old lists. Update tests,
docs and skills with the same semantics. Tighten individual quality properties
in later coherent replacements using the preserved whole-system assessment.

## Validation Strategy

Use independent fault cases: missing owner, duplicate selection, failed and
unknown prerequisites, empty/malformed result, exact source drift and successful
coverage-before-delivery. Verify that both entrypoints select the same required
closure for the same declared plane and that dynamic provider identities are
not mistaken for unused code. Run focused tests and static checks before exact
full proof, official archive, reproof, acceptance and installed readback.
