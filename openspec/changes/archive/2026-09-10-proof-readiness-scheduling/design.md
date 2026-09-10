## Context

Both proof and local CI consume the same runner. Its wave barrier waits for all
siblings before making another scheduling decision, even when a completed node
has unlocked useful work. The test gate has no cheap source prerequisites.
Neither problem requires another workflow engine or stored progress model.

## Decisions

Use one executor for an admitted graph. Track pending, running and completed
nodes only for the duration of the call. A node becomes runnable after all of
its dependencies finish; unsuccessful prerequisites produce a blocked result
without executing the node. Ready readers may fill free capacity. A ready
writer drains readers, runs alone and prevents new admission until completion.
Return results in canonical plan order, independently of completion order.
Validate graph and capacity before launching any command. Dry-run retains every
unknown result and executes no checks.

Declare source readiness in `system/gates.toml`, not a second phase list in
Python: lint, schemas, configuration, types and source budget precede tests.
The same dependency closure reaches public proof and local CI. Independent
checks still run, so useful diagnostic batching does not become global early
exit. Coverage, package creation and install retain their existing dependencies.

Delete the wave planner and migrate all consumers to the one graph executor.
Do not retain an alias or second scheduler. Existing write declarations remain
the conservative exclusion boundary; this change does not claim complete
resource-footprint inference for undeclared shared effects.

## Verification

Use bounded Event/Barrier handshakes rather than timing races: a child must
start while an unrelated predecessor is still waiting; a writer must never
overlap another check. Inject failed and unknown cheap prerequisites and assert
zero test/package executions while independent diagnostics remain. Exercise
serial/dry-run, invalid graphs, capacity and completion-order variation. Preserve
all proof identities, workload and coverage requirements. Compare controlled
serial and parallel workloads only within their measured scope.

## Full-Cycle Boundary

Execution evidence, current acceptance and effect-time authorization remain
separate. Reuse across source objects requires a proved complete input closure
and cold/warm/cache-cleared verdict equality in later work. This change removes
avoidable scheduling waits and late failure, not repeated computation itself.

## Specification Clarity

Official validation observed 25 INFO length issues in ten canonical specs. Its
successful exit does not mean issue-free source. Most affected requirements can
be expressed directly without changing their obligations. The oversized runtime,
intent-recovery and retirement aggregations have distinct owners or admission
boundaries and should split on those semantics. Retain every original scenario
exactly once. Use the quality delta for changed behavior; apply editorial
regrouping directly to admitted canonical specs without duplicate intent. Verify
native validation plus a before/after scenario multiset. Length is a diagnostic, not a reason to erase constraints or
move arbitrary paragraphs under cosmetic headings.
