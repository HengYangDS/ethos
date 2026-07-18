## Why

A local closeout run exposed a real evidence-boundary flaw: running the Python
owner test gate and `ethos prove --execute` concurrently can make both processes
clean, combine, or write the same generated coverage files under
`build/evidence/quality/tests/coverage/`. The tests may still pass, but the
latest coverage artifact can become a mixed projection and report a false
coverage floor failure.

ETHOS must treat this as an early disorder signal. The generated evidence root
is not a truth store, but a proof gate may rely on its latest artifact. Shared
writes to that artifact therefore need a small, repository-local serialization
mechanism.

## What Changes

- Serialize `run-python-tests.sh` coverage evidence writes with a POSIX lockdir.
- Keep the existing evidence root and coverage artifact path; no new truth store
  or parallel coverage location is introduced.
- Add an architecture regression test for the lock boundary.
- Document the generated evidence boundary in the Product Design Contract.

## Capabilities

- `repository-governance`: subject=ethos:evidence-run-isolation;
  reuse=extend; change=modify; facet:lifecycle=validation;
  facet:surface=ci,evidence,test,docs,openspec;
  facet:authority=script,test,contract,openspec,claim,evidence

## Out Of Scope

- No hosted CI provider rewrite.
- No change to the 100% coverage floor.
- No new evidence truth store or generated artifact promotion rule.
