## Context

`tools/ci/scripts/run-python-tests.sh` owns the trust-bearing Python test gate
and writes generated coverage evidence to
`build/evidence/quality/tests/coverage/`. `ethos prove --execute` can invoke the
same gate. Running both at the same time may race over cleanup and pytest-cov
SQLite shard combination.

## Design

Use a lock directory at `build/evidence/quality/tests/coverage/.write.lock`.
`mkdir` is atomic on the local filesystem and needs no extra dependency. The
script waits while the lock exists, acquires it before cleaning or writing the
coverage evidence directory, and removes it on exit through the existing cleanup
trap.

This is deliberately a physical evidence-boundary guard, not a semantic store.
The latest coverage XML remains generated evidence. Repository truth remains in
source, tests, config, scripts, OpenSpec, claims, and chronicle records.

## Alternatives

- Per-run coverage directories plus promotion: stronger but larger. It creates a
  promotion protocol that ETHOS does not yet need for this local generated
  evidence boundary.
- Ignore the issue because normal CI does not run two gates concurrently:
  rejected because local multi-agent operation already produced the failure.
- Use `flock`: rejected for portability and because POSIX `mkdir` is enough.

## Proof Strategy

- Architecture test checks the lock contract in the owner script.
- Focused owner-script architecture tests.
- Full local CI fallback.
- HEAD-bound `ethos prove --execute` before land.
