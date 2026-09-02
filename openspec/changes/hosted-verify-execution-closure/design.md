## Context

See [proposal.md](proposal.md). GitLab pipelines `6081` and `6082` execute the
same accepted object and each finish with `132 failed, 1855 passed, 1 skipped`.
The failures share one boundary defect: bootstrap and the Python test owner do
not compile a complete execution supply before pytest is lowered to uid/gid
65534.

The observed consequences are coupled, not four independent product features:
runtime-generation observation cannot invoke `ps`; descended tests reinterpret
the still-present run-as pair and attempt a second privilege drop; an offline
wheel build resolves a relative UV cache against its copied repository; and one
publication fixture replaces the source-bound OpenSpec resolver with a bare
ambient command.

## Goals / Non-Goals

**Goals:**

- Establish one complete execution environment before crossing the privilege
  boundary.
- Preserve locked, offline, exact-HEAD verification through nested subprocesses
  and copied repositories.
- Keep bootstrap, execution-environment compilation, and tool resolution under
  their existing distinct owners.
- Prove the boundary with focused regressions before changing implementation.

**Non-Goals:**

- No new execution-closure schema, registry, wrapper, daemon, or persistent
  state.
- No provider-specific fallback in product source and no ambient PATH/cache
  repair.
- No relaxation of warnings, offline mode, privilege isolation, proof scope, or
  hosted-plane attribution.
- No change to AIGW, Proxy, or another adopter.

## Decisions

### Bootstrap owns native prerequisites

The existing hosted bootstrap SHALL ensure that the Linux image supplies the
declared process-observation and identity-transition executables before any
proof command starts. This extends the current prerequisite check rather than
adding logic to GitLab YAML or teaching product code to install host packages.

Installing a fallback process observer in Python was rejected because it would
duplicate an admitted native capability and leave the image incomplete for
other consumers.

### The test gate consumes control inputs once

The Python test owner SHALL validate the requested run-as identity while still
privileged, use it only to construct the outer pytest command, and explicitly
remove the control pair from the child environment. Descended code therefore
observes its actual identity instead of receiving an instruction to repeat the
transition.

Retaining the variables and teaching every nested consumer to ignore them was
rejected because it distributes ownership of one boundary across the test
suite.

### Repository cache coordinates become absolute before execution

When a repository-owned cache path is declared, the test owner SHALL resolve it
against the original repository before pytest starts and project that absolute
path to descendants. A copied repository can then perform an offline build
against the already provisioned locked supply without interpreting its own
working directory as a second cache authority.

Copying caches into each temporary repository and enabling network fallback
were rejected because both increase state, IO, and non-determinism.

### Tests use the production resolver boundary

A fixture that needs OpenSpec SHALL retain the existing source-bound absolute
resolver. Replacing it with `("openspec",)` tests an ambient installation that
the product explicitly rejects; that fixture is removed rather than supported.

## Risks / Trade-offs

- **Risk:** a read-only shared UV cache may be exercised by concurrent nested
  builds. **Mitigation:** UV's cache is already the locked tool supply owner; the
  test projection only stabilizes its coordinate and does not add another
  writer or cache.
- **Risk:** bootstrap package names are Linux-distribution-specific.
  **Mitigation:** they remain confined to the existing Debian-family hosted
  bootstrap and are verified by its architecture contract.
- **Risk:** environment removal semantics could differ across runners.
  **Mitigation:** focused tests inspect the exact environment passed to the Nox
  session, and hosted verification proves the real provider boundary.

## Migration Plan

1. Add failing regressions for native prerequisite supply, one-time run-as
   consumption, and absolute cache inheritance.
2. Extend the existing bootstrap and Python test owner with the minimum changes
   required by those regressions; delete the ambient OpenSpec fixture override.
3. Run focused tests, strict OpenSpec validation, and exact-HEAD full proof.
4. Archive and reprove, then advance candidate and accepted refs by exact CAS,
   materialize a fresh package-only runtime, publish the same object to both
   remotes, and observe each hosted plane independently.
