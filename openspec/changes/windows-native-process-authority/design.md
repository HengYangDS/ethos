## Context

See [proposal.md](proposal.md). The failure appears during immutable runtime
cleanup, but the underlying ownership defect is broader: the shared non-Git
runner lives in `adapters/repo/git.py`, so a PowerShell spawn failure is labeled
as Git and loses the command boundary that failed. A separate trust-anchor
adapter already demonstrates the correct Windows authority source:
`SYSTEMROOT/System32/WindowsPowerShell/v1.0/powershell.exe`.

## Goals / Non-Goals

**Goals:**

- give shared external process creation one provider-neutral owner;
- keep Git-specific resolution and failure vocabulary inside the Git adapter;
- make all current shared-runner consumers use the replacement owner directly;
- select Windows PowerShell once from the native operating-system root;
- preserve exact creation diagnostics without broadening `PATH` or retrying.

**Non-Goals:**

- no shell discovery fallback, executable search registry, retry layer, or
  Windows compatibility wrapper;
- no rewrite of specialized streaming, gate, build, or handoff subprocess
  adapters whose process interaction is itself their bounded native effect;
- no tempfile, publication, lane, or adopter repair in this Change.

## Decisions

### 1. Replace the misplaced generic runner

Create one public `ethos.adapters.process` module. A package would add an empty
namespace around one implementation module, so the single module is the
semantic owner. It owns exact argv execution, the inherited-environment
projection currently required by shared callers, and a structured
`ProcessExecutionError`.

`adapters/repo/git.py` delegates actual creation to that adapter and translates
only failures of Git commands into `GitExecutionError`. The old generic
`run_command` and raw `_execute` owner leave the Git module. OpenSpec, hook,
runtime, and trust-anchor callers import the process owner directly; no facade
or compatibility alias remains.

Alternative rejected: only replace the literal `powershell.exe`. That would
make the hosted test pass while retaining the false Git ownership and lossy
diagnostic boundary.

### 2. Resolve one native Windows PowerShell

The process adapter derives the sole Windows PowerShell path from
`SYSTEMROOT/System32/WindowsPowerShell/v1.0/powershell.exe`, validates that it
is a file, and returns no ambient fallback. Runtime consumer observation and
trust-anchor protection reuse this resolver. The latter continues to remove an
incompatible inherited `PSModulePath` for its security-module operation.

Alternative rejected: add the PowerShell directory to the isolated smoke
`PATH`. That would weaken the test and retain host PATH ordering as authority.

### 3. Preserve creation evidence at the boundary

`ProcessExecutionError` binds a stable code and reason to exact argv, resolved
working directory, and the original `OSError` description. Exception chaining
retains the native exception object. Public CLI and hook-install projections
render those fields as evidence while keeping one stable required-gap code.

## Risks / Trade-offs

- **Existing tests patch the Git module's generic runner** → migrate tests to
  patch the concrete process owner or the consuming module; retain no alias.
- **Windows path behavior cannot be executed natively on macOS** → unit tests
  inject a temporary `SYSTEMROOT`, while the isolated-wheel hosted matrix is
  the final platform proof.
- **A broad subprocess rewrite would make this Change unbounded** → migrate only
  consumers of the incumbent shared runner. Specialized process adapters remain
  explicit owners and are separately auditable.

## Migration Plan

1. Add RED tests for native PowerShell selection and structured non-Git spawn
   failure evidence.
2. Add the process module, delegate Git execution, and migrate every incumbent
   `repo.git.run_command` consumer.
3. Delete the old generic runner, close references, and update the terminal
   convergence projection with the observed hosted boundary.
4. Run focused verification, commit, exact-HEAD full proof, official archive and
   reproof, candidate and accepted CAS, immutable runtime readback, dual-peer
   publication, and hosted Windows Python 3.12/3.13/3.14 verification.
