## Context

At campaign start, `system/tools.toml` declared 54 mechanisms, while proof policy
and documentation did not consistently reflect those declarations. Import-linter was
active but its gate bypasses the owner script and is absent from proof sets;
deptry is active without a GateDescriptor; vulnerability docs still name
`pip-audit` although the owner runs `uv audit`; and release metadata uses SPDX
and SLSA names for ETHOS-local projections. The repository also lacks durable
decisions for dead code, clones, API compatibility, mutation/fuzzing,
benchmarks, package contents, workflow security, license compliance,
reproducibility, test isolation, SBOM validation, and supply-chain adapters.

## Goals / Non-Goals

**Goals:**

- Repair the currently proven import/dependency owner-to-proof breaks and make
  one gate-registry-derived execution plane the explicit next convergence wave.
- Select the smallest independent tool for each uncovered capability.
- Preserve deterministic, offline, owner-scripted default proof.
- Keep future pilots explicit without installing them prematurely.
- Correct claims that exceed the implemented standard contract.
- Name gate-registry closure and tool-supply closure as prerequisites to new
  external pilots rather than pretending the current projections are derived.

**Non-Goals:**

- A universal quality platform or hosted dashboard.
- Multiple permanent tools for the same capability.
- Treating similarity, mutation, fuzz, benchmark, or hosted observations as
  proof of correctness by themselves.
- Auto-updating dependencies, source, or releases from an external service.

## Decisions

### 1. Capability first, tool second

The roadmap owns comparative decisions. `system/tools.toml` records admitted
active mechanisms only. A time-bounded OpenSpec pilot owns candidate config,
supply, runner, evidence, and expiry outside that catalog; the tool receives a
runtime catalog row only on promotion. Deferred and rejected alternatives
receive no runtime catalog row, config, runner, or gate.

### 2. Repair active truth before adding tools

Import-linter and deptry join the default and full proof floors through their
existing owner scripts. Pre-commit config validation joins
`run-config-lint.sh`; provider files and hooks continue to invoke owner scripts
only. This Change does not claim that every active catalog mechanism already has
a trust-bearing GateDescriptor or that every execution plane is registry-derived.

### 3. Portfolio boundary

The tooling roadmap is the sole ranked active, pilot, deferred, and rejected
decision surface. This Change adds no candidate runtime row; it records only the
change-specific evidence and rationale below.

The current clone-compression pilot incumbent is find-dup-defs because its JSON
is byte-stable and it reports actionable production and test helper clusters.
It is not an admitted owner. pyscn remains an on-demand cohesion/architecture
challenger with clone analysis disabled only after it supports the Python 3.14
baseline; its raw report includes timestamps, durations, and unstable ordering.
jscpd is cross-language lexical diagnosis only. None may coexist permanently
with an equivalent ETHOS-native redundancy gate.

Vulture is rejected after a read-only repository pilot: its 90% confidence run
reported only the dynamically loaded build hook, while lower confidence flooded
on Pydantic and Cyclopts declarations. A permanent allowlist would add more
policy than the tool deletes.

xdist remains a scheduling mechanism rather than concurrency proof; coverage
remains reachability evidence rather than assertion adequacy. Stateful,
metamorphic, race, mutation, random-order, leak, and benchmark mechanisms keep
separate claims and only replace weaker tests when they prove net value.

### 4. Pilot exit contract

A candidate must prove deterministic repeated output, independent findings,
bounded runtime and supply, no undeclared network or write behavior, and a
measurable benefit on two real changes. The terminal decision is exactly one of:
promote the external tool, absorb its useful rule into an existing owner and
retire it, or reject it.

### 5. Standard names require standard proof

The current SBOM and provenance outputs remain ETHOS-local projections. Syft is
admissible only as a replacement for the native SPDX-lite builder, with the old
code and tests deleted in the same Change; official SPDX tooling then validates
the generated standard rather than duplicating generation. Registry-native
provenance is preferred where publication supports it. Cosign is reserved for
detached blobs after exact artifact digests and a verification flow exist; none
of these names proves SLSA conformance by itself.

## Risks / Trade-offs

- [Risk] Two additional default gates increase proof latency. → Reuse existing
  cached owner scripts and measure the post-change proof duration.
- [Risk] Pilot residue becomes permanent backlog. → Give every candidate an
  explicit promotion evidence bar and retirement/rejection exit, and forbid a
  runtime catalog row before promotion.
- [Risk] Tool comparisons become a second documentation truth. → Keep the
  existing roadmap as the only comparative decision surface and derive CLI tool
  profiles from `system/tools.toml`.
- [Risk] A formatter pilot rewrites ecosystem-native files destructively. → Run
  formatter candidates report-only until fixtures prove stable output.

## Migration Plan

1. Repair active gate and documentation truth with no external pilot enabled.
2. Land the portfolio decisions, remove non-executable catalog backlog, and
   correct release-boundary wording.
3. Close gate-registry projection and tool-supply truth before external pilots.
4. Run later pilots one capability at a time in separate OpenSpec Changes.
5. Delete rejected pilot config, runner, cache, and dependency in the same
   Change that records the rejection.
