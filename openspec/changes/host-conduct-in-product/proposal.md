# Proposal

## Why

The owner directed on 2026-11-15, and stated again on 2026-11-17, that common law and common
mechanisms come from ETHOS and not from each repository's or each session's own means. On a
workstation that several sessions share, the conduct around the host queue is such common law,
and most of it is still kept outside the product. Measured on the releasing host on 2026-11-17:

- The host's owner keeps the conduct in one prose file in the home directory, which every agent
  receives as instructions. It holds eight rules. The product reads the declaration of slots,
  reserved CPUs and the load limit; it reads none of the eight.
- Light work has no reader. The rule gives a session a small share of cores for work that takes
  no ticket. One session ran three one-worker test runs together beside another session's proof;
  measured afterwards they held about 2.3 to 2.5 cores, over that share, while the 1-minute load
  stood far above the declared limit. No command refused or reported it.
- The repair was private twice. That session wrote a script that takes one lock for every test
  run and logs each run's CPU time over its wall time. The session that keeps the host's record
  wrote its own script for the same measure. Two sessions now hold two tools for one rule.
- The queue keeps no log, so each session sends a start line and a done line for every ticket to
  the keeping session by message, and the review of the rules reads those messages.
- The cap of tickets for one session is counted by each session from the queue's files before
  it enters. `host-reservation-guests` measured four tickets of one session at once.
- A brief pointed a preparation agent at the rules' file, which only its owner may read. The
  agent opened it. A rule that lives in a private file cannot be cited by a tracked document.
- Heavy work that must outlive the session that started it has no ETHOS form: `ethos host run`
  holds a ticket only while its parent lives. An application quit on 2026-11-13 ended four
  detached chains of two sessions, and a restart on 2026-11-17 ended every background process.
  Two sessions wrote two private launchers for the one need. A candidate: a ticketed run detached
  from its caller, whose unit belongs to the host's service manager, with a record in the host's
  store that `ethos host status` reads.
- A capped suite's start below the load bound rests on each session's own wrapper. On 2026-11-19
  one session's test runner went around its wrapper four times in a night, and the fourth run
  started above the bound; the runner now refuses to start outside the wrapper or a ticket.

Where each rule's subject stands in ETHOS today:

| Subject of the host's rule                    | In ETHOS                                         |
| --------------------------------------------- | ------------------------------------------------ |
| The declaration is not overridden             | built: the product reads the host declaration    |
| Heavy work runs as the child of one ticket    | built: `ethos host run`; nothing detects a miss  |
| A session's light work stays within a share   | not held anywhere                                |
| A cap of tickets for one session              | designed in `host-reservation-guests`, not built |
| No two tickets do the same work for one head  | not held anywhere                                |
| A guest pipeline starts under one ticket      | candidates in `guest-pipeline-admission`         |
| Consecutive heavy commands may share a ticket | not held anywhere                                |
| Start and done lines as the queue's record    | a candidate in `guest-pipeline-admission`        |

## What Changes

Intent, not yet designed. Each line is a mechanism that ETHOS provides so that the matching
prose rule can leave the host's file:

- A light run: a command that a session runs without a ticket goes through one ETHOS verb, which
  holds the session's one light place, measures the run's CPU time over its wall time with every
  descendant, and writes the reading to the host's record. It reports first; whether a run over
  its share is refused is decided with the design.
- The queue's own record of every admission and release, with the holder, the repository, the
  head and the stated work, so that "the same work for one head" and a session's ticket count are
  read from one place and no session reports by message.
- The declaration gains the conduct's values (a session's light share, the cap of tickets, the
  bound of a shared ticket), so that the prose file restates none of them.
- `ethos host status` names what the rules ask a session to check before it enters.
- `ethos host run` prints one line when its command is admitted, so that a caller's log tells
  queued from admitted. Two sessions built that line themselves on 2026-11-19, and one built
  three readers of the queue before it found `ethos host status --json`.
- The cap of a session's tickets is enforced by the queue, by the ticket's owner. Each session
  counts its own tickets today; one session's counter had a race on 2026-11-18.

Not here: the cap's own design and the declared CPU share (`host-reservation-guests`), and the
guest pipeline's resource (`guest-pipeline-admission`). This draft names the rest and the order
in which the prose rules retire.

Not breaking: nothing is built by this draft.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The host adapter and its verbs (`ethos host run`, `ethos host status`), the host declaration and
the queue's store. Inputs received and not yet weighed: the keeping session's readings of its
record, and a second session's recommendation that tickets declare CPUs and that the declaration
holds a cap for each repository. Not measured: how many light runs a session makes a day, and
the cost of the measure on a run of a few seconds.

Owner: the release lead. Next action: a study that sizes the light run and the queue's record,
with the keeping session's record as its data. Read again: at the cut of 2026-11-26.
