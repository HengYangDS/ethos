# Design

## Context

`evaluate_dependency_acceptance` decides whether the findings of an audit observation are
covered by the policy's records. `tests/unit/ci/dependency_audit/test_acceptance.py` exercises
that decision with records that each test builds, and one test there holds the lock digest of
each committed record against the committed lock. Nothing holds a committed record's nodes and
versions against the lock, and nothing shows that the committed records cover their findings:
that pairing is checked only when an audit runs and a finding is present.

## Goals / Non-Goals

Goals:

- A commit that moves the lock or edits a record fails a test when a record no longer names an
  artifact of the lock.
- The committed records are shown to do what they say: they cover their findings before their
  end and stop covering them from it.

Non-Goals:

- Reading the clock. A record that has reached its day is the audit's finding on that day; this
  test passes the times that it compares, so it does not start to fail on a date.
- Any change to the decision, the policy's shape or a record.

## Decisions

1. **The subject is the committed files.** The module reads the policy and `package-lock.json`
   from the repository root. Alternative, not taken: fixtures of both, which would test the
   decision again and leave the committed pairing unchecked.
2. **The product's decision judges the records.** The second test builds the report that npm
   would give for exactly the findings the records name, with the nodes, versions and
   integrities that the lock supplies, and calls `evaluate_dependency_acceptance`. Alternative,
   not taken: matching records against the lock in the test, a second copy of the product's
   rule.
3. **A module of its own, and the one owner of these checks.** The earlier test of the lock
   digest moves into it and keeps its assertion for every record; a production record must name
   the digest. `test_acceptance.py` stands at the ceiling of 500 effective lines for one file.

## Risks / Trade-offs

- A supply move that leaves a stale record now fails this module. That is the purpose: the move
  updates or removes the record in the same commit.
- The report that the test builds follows npm's present shape through the suite's shared
  `clean_report`; a change of that shape is repaired there, in one place.
