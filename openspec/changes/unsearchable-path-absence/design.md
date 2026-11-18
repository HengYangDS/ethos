# Design

## Context

See [proposal.md](proposal.md).

- **The walk.** `_native_path_prefixes` walks each absolute path of the process listing, of the
  worktrees' Git configuration values and of the interpreter bindings, one component at a time,
  and records every prefix that is there. `_native_path` answers one step: it asks whether the
  name is there, then resolves it strictly. A reference inside a generation therefore records the
  generation's own directory before the walk reaches what lies inside it.
- **Two answers.** The step asked `Path.exists`, `Path.is_symlink` and `Path.is_dir`. Before
  Python 3.14 these raise below a directory that the process may not search; from 3.14 they answer
  no. A probe that compiles the two readers' own function text ran on Python 3.12.16, 3.13.18 and
  3.14.10 at the base `4a5029e96`: for a listed name below such a directory the walk raised
  `PermissionError` under 3.12 and 3.13 and recorded the prefixes above it under 3.14; the
  consumer reader raised under 3.12 and 3.13 and answered `absent` under 3.14.
- **Who reads the walk.** Six consumers: the reclamation of generations and of wheel packages,
  the host store's retention, the plan of installations pinned before consumers were recorded,
  and the plan and the gate of an exit. Each reads an error of the walk as a deferral, an
  unknown or a gap.
- **The consumer reader is no longer this Change's.** `_consumer_state` asked the same two
  questions of a consumer's path before its guard. The first form of this design gave it
  `absent`. The move of the release head of 0.2.0-beta.11 then repaired that reader by the
  owner's decision of 2026-11-17: it asks the host for the path's status and answers `unknown`
  for a place that cannot be looked at, on every interpreter, because the plan of installations
  pinned before consumers were recorded holds no installation for an absent consumer. That
  repair stands, and this Change does not touch the reader.

## Goals / Non-Goals

Goals:

- One answer on Python 3.12, 3.13 and 3.14 for a listed path below a directory that the observer
  may not search: absent.
- A link that is there and cannot be resolved stays an unknown observation.

Non-Goals:

- Releasing an absent consumer. The Change `store-retention` owns it and reads absence itself.
- Classifying the other callers of the same path questions in the product.
- The reader of a consumer's state, which 0.2.0-beta.11 repaired to `unknown`.
- A new refusal, or a change of which paths are observed.

## Decisions

1. **A listed path below a directory that the observer may not search is an observed absence.**
   - **Rests on:** the owner's decision of 2026-11-17, taken on three ways shown with their
     costs; the probe of the Context; the repair of the reader of record writers in
     `full-suite-legs`, task 6.7, which gave that reader this answer on the three interpreters.
   - **Considered:** every reader answers unknown, which makes one such process on a host defer
     every cleanup and takes back that repair; unknown only for a place inside the repository's
     own roots, which computes those roots before each observation and holds the most code.
   - **Chosen because:** it is the answer already in effect wherever ETHOS runs Python 3.14, and
     a place that cannot be looked at gives the observer nothing to retain. This decision
     supersedes one sentence of the archived design `2026-10-26-listed-path-absence`:
     "Permission errors and `NotADirectoryError` also stay unknown". That sentence was written
     for the resolution of a name that is there, and it still holds for it (decision 2); it no
     longer holds for a name that the host does not let the observer look at. The trade-off that
     the owner accepted: a process that runs from an owned generation whose directory was made
     unsearchable is not seen as that generation's consumer. `NotADirectoryError` keeps its
     meaning after the change: it arises where a link that is there names a place through a
     regular file, and that link stays unknown (decision 2). A listed name below a regular
     file never raised it: it answered absent before, on the three interpreters, and still
     does.
   - **Applies to:** every caller of the walk, on POSIX and on Windows. How far the trade-off
     reaches, measured with the walk on the three interpreters: a generation whose own directory
     may not be searched is still retained by a path listed inside it, because the walk records
     the directory before it asks about its inside; an alias of a generation that lies below
     such a directory is not followed, so that listing does not retain the generation. It does
     not cover a process listing that cannot be read, which still defers.
2. **A link that is there and cannot be resolved stays unknown.**
   - **Rests on:** the lead's condition; the probe: a listed link whose target lies below such a
     directory raises `PermissionError` at its resolution, a dangling link `FileNotFoundError`,
     and a link whose target runs through a regular file `NotADirectoryError`, on the three
     interpreters before and after the change.
   - **Considered:** reading every resolution error as absent, which the archived design
     rejected because it hides the permission and filesystem faults that the contract treats as
     unknown.
   - **Chosen because:** a link is a statement that something lies elsewhere. When the observer
     cannot follow it, what it names may be a generation, and the contract defers deletion for
     an unknown observation.
   - **Applies to:** the strict resolution of a name that is there. In the probe, after the
     change, a permission error and a `NotADirectoryError` left the walk from that resolution
     alone, on the three interpreters.
3. **The reader asks one question that does not raise, and no helper is added.**
   - **Rests on:** the probe's column for `os.path.lexists`: it answers no for a name that
     cannot be looked at on the three interpreters, and yes for a link whatever it names; 22
     uses of it in 10 files of `src` at the base (`git grep -c`).
   - **Considered:** a second guard helper like the one of the reader of record writers, which
     repeats that helper's body in another module; moving that helper to a shared owner, which
     changes a module that this Change leaves alone; classifying the error where it is caught,
     which needs a guard of its own for the link question before Python 3.14.
   - **Chosen because:** it replaces one question in the reader, and the product's source budget
     does not grow. The trade-off: before Python 3.14 any error of the host at the name's own
     entry now reads as absent, as it already does from 3.14, and no longer only a permission
     error.
   - **Applies to:** `_native_path`. The directory question is asked only of a name that is
     there.
4. **The regression of a path deleted while it is observed follows the question.**
   - **Rests on:** a mutation run in the preparation clone: with the reader's handling of a
     deleted path removed, the existing case still passed after decision 3, because it deleted
     the path inside `Path.exists`, which the reader no longer calls.
   - **Considered:** leaving the case as it was, which keeps a regression that can no longer
     fail.
   - **Chosen because:** a regression that cannot fail protects nothing. The case now deletes
     the path inside the question that the reader asks and asserts that the deletion happened;
     with the handling removed it fails.
   - **Applies to:** `test_listed_path_deleted_while_observed_is_an_observed_absence`.

## Risks / Trade-offs

- Under Python 3.12 a selector that names a local runtime which links to itself ends the host
  store's cleanup with an error that no caller catches; from 3.13 the same loop is an operating
  system error and reads as an unknown consumer. Read in the code and not run. It stays an open
  task of this Change, with a failing case first.
- A regression that needs a closed directory is skipped for the superuser and on Windows. Where
  a suite leg runs as the superuser, the new cases are skipped there and prove nothing; whether
  a hosted leg does was not read.
- The new cases pass under Python 3.14 before the change, except the case of decision 4. They
  prove the repair only on Python 3.12 and 3.13, which the tasks require.
- Windows is covered by reasoning only: a directory that a user may not traverse is rare there,
  and no case runs it.
