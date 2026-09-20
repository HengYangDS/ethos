---
subject: ethos:foundations-execution
role: research
state: active
relations:
  part_of: ../modern-engineering-foundations.md
  informs: ../../plans/terminal-governance-product-design.md
  constrained_by: ../../governance/product-design-contract.md
---

# Execution And Evidence Reuse

Status: active research; dated observations retain their original evidence limits.

Purpose: Compare native and container execution foundations against the same workload.

See also: [Research Overview](../modern-engineering-foundations.md),
[Product Design Contract](../../governance/product-design-contract.md), and
[Terminal Plan](../../plans/terminal-governance-product-design.md).

## Execution, Reuse And Failure Latency

[Pants][pants] is the leading native dependency-aware execution candidate to
compare with the current scheduler. Its [process implementation][pants-process]
has explicit cache scopes, including per-session deduplication without durable
reuse. Dependency inference, declared environment inputs and process isolation
can remove home-grown selection/materialization/cache logic. They do not infer
all mutable Git metadata, lock owners, credentials, remote facts or undeclared
host observations. Native Windows coverage remains unestablished by this review.

[Dagger][dagger] is the leading containerized build/package execution candidate.
The inspected release offers typed container/file/Git operations, reusable
execution and OpenTelemetry output. It can replace repeated CI shell and container
setup while keeping local and CI invocations aligned. A container running on a
Mac does not test native macOS process/file semantics; Linux containers do not
replace native Windows verification. A mutable cache volume is not an immutable
proof input, and a Git mirror is not itself the selected source snapshot.

[Bazel][bazel] and Nix are comparison references when their execution or supply
model fits better. They are not rejected because the repository has one package,
nor admitted because they are large foundations. Selection requires the common
workload below. Native tests and governed mutable effects may legitimately remain
outside a selected build engine, under one explicit resource contract.

Current replacement targets are the scheduling/process portion of
`src/ethos/adapters/gates/runner.py`, repeated setup in
`tools/ci/python_test_gate.py`, and materialization under
`src/ethos/adapters/repo/runtime/materialization/`. Do not delete the gate
obligation registry, proof binding, native effect tests or immutable runtime
selection merely because an engine can execute commands.

Optimize the whole feedback interval: cheap deterministic failures first;
reuse an unchanged, still-applicable execution result; do not replay a heavy
suite to change presentation; freeze before full proof; observe real effect
results before retry. A dependency-aware queue already exists, so the next
comparison concerns input completeness, setup duplication, isolation and process
lifetime, not a superficial scheduling rewrite.

## Sources

Links identify inspected documents, not blanket endorsements. Source-level and
README observations above have different strength; repository popularity and
marketing claims were not used as evidence of comparative performance.

[pants]: https://github.com/pantsbuild/pants/blob/c94f9f4ccfd43342b8f9379a139a328555bc5a5b/src/python/pants/engine/process.py
[dagger]: https://github.com/dagger/dagger/blob/f2aefc20cf41b5ed7922df7244e0f10ddc6031f7/README.md
[bazel]: https://github.com/bazelbuild/bazel/blob/aac8677f8e69e30fb105026ff524e04965640499/README.md
[pants-process]: https://github.com/pantsbuild/pants/blob/c94f9f4ccfd43342b8f9379a139a328555bc5a5b/src/python/pants/engine/process.py
