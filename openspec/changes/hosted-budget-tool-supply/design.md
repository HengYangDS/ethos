## Context

A fresh Linux runner has the locked Python/Node environment but no `scc`.
The source-budget gate therefore blocks; later gates are not test failures.
A successful maintainer-host proof did not establish a closed hosted toolchain.

## Decision

The existing budget declaration owns a pinned native-tool supply. A bounded
installer verifies the official archive before extraction, checks executable
version, and atomically publishes only its executable in the repository tool
cache. It neither trusts ambient PATH nor writes system directories. Existing
bounded download transport is reused. Linux and Darwin ARM64/x86_64 share this
owner; unsupported platforms fail before mutation of the installed executable.

Cache reuse verifies the archive and compares its member bytes with the current
regular executable, then observes the version without changing file identity.
Only missing, damaged or non-executable supply creates a temporary replacement.
This removes repeated extraction and executable identity churn while preserving
fresh validation; a prior successful invocation is never sufficient authority.
The existing installer owns comparison, temporary lifetime and atomic replacement
in one Python operation rather than splitting lifetime across shell and Python.

The shared hosted-proof entry prepares this supply before executing any gate,
then exposes its exact directory through child PATH. Preparation failures flow
through the existing non-passing receipt/diagnostic path. Neither Forge gains
an installer, budget policy or semantic parser of its own.

## Verification And Boundaries

Exercise real installer processes with isolated archive fixtures: clean setup,
verified cache reuse, replaced executable tampering, bad digest, wrong version,
missing executable, unsupported target and transport failure. Run the shared
wrapper to prove a supply error never invokes proof and removes stale evidence.
Run the actual pinned binary against current source-budget inputs. Full proof,
accepted runtime, and hosted jobs are separately required closeout observations.
This Change does not claim general crash-atomic installation or hostile same-UID
process isolation. Its temporary preparation directory is owned and removed.
Verify stable inode and modification time on unchanged repeat calls, repair of
mode and symlink damage, and rejection of archive tampering even after a valid
installation. Measure cold/warm native execution separately; this optimization
does not establish the cause of hook-query or process-observation failures.

## Hosted Verification Prerequisites

The accepted hosted run exposed an archive fixture that captured UTC date at
collection while the production owner read it at execution. The fixture now
supplies one explicit clock and matching archive path, exercising both dates
around the observed midnight with real Git collisions and preservation. The
production date semantics remain unchanged; moving a live clock read later
would merely shorten, not eliminate, the race.

A separate executed child-origin counterexample showed the POSIX shell fixture
retained its parent Python prefix, leaving its source-selecting `.pth` inert.
The existing fixture now uses a native executable with `pyvenv.cfg`, sharing
the base standard library and dependency site-packages without copying their
trees. Its isolated child must report its own prefix and selected source,
including when that source differs from the parent environment. Runtime link
and inode checks remain unchanged. The materialization fixture binds dependency
selection to its explicit test interpreter, not another checkout's `.venv`.
This corrects verification identity; native copies are not claimed faster.

The native hardlink retirement failure remains unexplained. Serialize complete
existing result evidence in assertions, including `process_failure`, rather
than truncate its cause. Do not relax observation completeness, retry admission
implicitly, or classify later focused success as a root-cause repair. Keep that
uncertainty and source-bound full proof as distinct acceptance obligations.
