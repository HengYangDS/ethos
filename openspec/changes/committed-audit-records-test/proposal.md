# Proposal

## Why

The repository's audit policy, `.config/checks/dependency-vulnerabilities/policy.toml`, holds
acceptance records. Each one accepts a named finding of the committed npm lock until a day: it
names a package, a version, the lock's nodes and, for a production record, the lock's digest. A
supply move changes the lock. A record whose node or version has left the lock then accepts
nothing, and nothing says so until the audit next runs with that finding. The review of the
supply move of 2026-11-18 asked for a test that holds every committed record against the
committed lock, so that a stale record fails in the commit that makes it stale.

## What Changes

- A test module holds each committed record against the committed lock: a record that names a
  lock names this one, a production record names it, and each node that a record names, or
  every locked node of its package and version when it names none, exists in the lock with that
  package and version. The earlier test of the lock digest moves into this module.
- The same module asks the product's own decision with the native report that npm would give for
  exactly the findings the records name: one second before the first record ends, every record
  authorizes its finding; at the last record's end, the decision blocks and lists each record as
  expired.

Not breaking: tests only.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No requirement changes, so `skip_specs: true` applies.

## Impact

`tests/unit/ci/dependency_audit/test_committed_records.py`, a new module, and
`tests/unit/ci/dependency_audit/test_acceptance.py`, which gives it one test.
