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
