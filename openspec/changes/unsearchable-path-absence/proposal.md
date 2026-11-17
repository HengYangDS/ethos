# Proposal

## Why

Before it reclaims a runtime generation, and before it retires records, ETHOS reads the host's
process listing and resolves each path that a command line names. A path below a directory that
the observing user may not search gets two answers from one release. Measured on 2026-11-17 at
the release head of 0.2.0-beta.11, with one probe on three interpreters:

- Under Python 3.12 and 3.13 the reclamation reader raises the permission error. The
  reclamation then defers, as for an unknown observation.
- Under Python 3.14 the same reader answers that the path is absent, and the reclamation goes
  on.

The archived design `2026-10-26-listed-path-absence` chose the first answer: "Permission errors
and `NotADirectoryError` also stay unknown". Each of the ten ETHOS runtimes read on the releasing
host runs Python 3.14, so the second answer is the one in effect there. The reader of record
writers held the same difference: under Python 3.12 and 3.13 `ethos hook retire-records --apply`
deferred every batch. The batch of 0.2.0-beta.12 repaired that reader to the second answer on
all three interpreters (`full-suite-legs`, task 6.7).

The owner decided on 2026-11-17, on three ways shown with their costs: both readers read a place
that the host does not let them look at as absent, a new decision supersedes the archived
sentence, and the reclamation reader is aligned in 0.2.0-beta.13. The two ways not taken: both
readers answer unknown, which makes one such process on a host defer every cleanup and takes
back the repair above; and unknown only for a place inside the repository's own roots, which
needs those roots computed before each observation and holds the most code.

## What Changes

Candidates for the design, the first decided by the owner:

- The reclamation reader answers a listed path below a directory that it may not search as an
  observed absence on every supported interpreter. Behavior changes under Python 3.12 and 3.13
  and stays under 3.14. No refusal is added.
- A link that is present and whose target cannot be looked at stays an unknown observation and
  defers, as a dangling link does today (the lead's condition, for the design to confirm).
- The requirement "Generation reclamation uses fresh operational facts" gains one sentence and
  one scenario for this reading. A process listing that cannot be read at all still defers, as
  its scenario states.
- The cases of both readers run on Python 3.12, 3.13 and 3.14.

The trade-off that the decision accepts: a process that runs from an owned generation whose
directory was made unsearchable is not seen as that generation's consumer. On the releasing
host, 0 of 818 command lines read on 2026-11-17 raised a permission error.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

`src/ethos/adapters/repo/runtime/retirement.py` and its tests. Not measured: a Linux host that
other users' processes share, where such places are more common, and the other callers of the
same path predicates in the product, which this draft does not classify.

Owner: the release lead. Next action: design, delta and tasks for the batch of 0.2.0-beta.13.
Read again: at the cut of 2026-11-19.
