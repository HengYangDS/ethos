---
subject: ethos:guide:ci-guest-host
role: how-to
state: active
relations:
  canonical_for: running CI guests beside ETHOS on one host
---

# CI Guest Host

Status: active.
Purpose: size and read the host declaration on a host that also runs CI guests.

See also: [Command Plane](../reference/command-plane.md) for the exact commands and results.

Heavy ETHOS work — a full proof, `ethos host run`, a foreground host proof — shares one queue per
host. A host that also runs virtual machines for CI serves them from the same CPUs, so declare the
share and check it before a measurement.

## 1. What Shares The Host

- The queue: at most the number of slots that `host.toml` declares run heavy ETHOS work at a time.
- The guests: each virtual machine's vCPUs are CPUs that no admitted work may count as free.
- Renders: run them under `ethos host run`, so they take their place instead of competing silently.

## 2. Size The Declaration

`host.toml` in ETHOS's host root takes `slots`, `reserved_cpus` and `load_limit`, and nothing else:
a release that predates a key refuses the whole declaration.

- `reserved_cpus` is every guest's vCPU count, summed. Read the numbers from the guests' own
  configuration; ETHOS reads no hypervisor.
- `load_limit` is the 1-minute load a full proof waits under before its test and package gates.
  Something above the guests' own idle load keeps proofs from waiting forever on their own host.
- `slots` is how many heavy runs may share the host; one is the default. The slots share the CPUs
  that the reservation leaves, so each run's worker cap is that number divided by the slots.

`ethos host status --guest-cpus <N>` reports whether `N` fits inside `reserved_cpus` and answers
`host_reservation_exceeded` when it does not, with the value to declare as its next action. A
declaration reserves fewer CPUs than the host has. When the guests hold as many virtual CPUs as the
host has, or more, no value fits: the next action then names the guests' sizes, and
`data.reservation.reservable_cpus` is the most they may hold in total. Resizing a guest is its
owner's decision. The read removes nothing and names no repository path.

The load limit is the host's declaration in `host.toml`, and its owner changes it there from
measurements. The product reads an explicit `ETHOS_PROOF_HOST_LOAD_LIMIT` before the declaration
and records which of the two supplied the limit, so a run that set the variable is visible in its
admission record. Do not set it to start a proof on a busy host: a proof admitted above the declared
limit can lose a gate to its time bound. The ticket decides the queue at any load.

## 3. Read The Queue

`ethos host status --json` returns the declaration, the 1-minute load and every live ticket in
arrival order, each `holding` or `waiting`. A holder shows its operation, executable, process and
start time; the owner mark that the holder declared appears only to a session of the holder's own
repository. A contended wait names its holder as
`host_admission_contended:<operation>:<pid>:<since>`, and its next action is this read.

A run or a proof keeps its place behind tickets whose holders live, however long they run, so a
proof needs no wrapper to hold it. A ticket's lock shows that its holder lives, and a holder that
dies frees its place. A wait ends at `--wait <seconds>`, the caller's own total for
`ethos host run`, and at the latest at the admission ceiling, the declared maximum of
`timeout.admission_seconds`: 36,000 seconds. A holder that lives and hangs therefore holds its
waiters until then; this read names its process, and ending that process frees the place. The
repository's `timeout.admission_seconds` still bounds, as one total, a full proof's waits for its
repository's slot and for calm load; the time behind a live holder of the host slot is left out.
An engine of an earlier release in the same queue still ends its wait at its bound in total.

## 4. Run A Render

```bash
ethos host run --work <name> -- <render command>
```

The render takes its place in the queue and receives `ETHOS_HOST_CPU_CAP` and
`PYTEST_XDIST_AUTO_NUM_WORKERS`: one slot's share of the CPUs that the declaration leaves. A worker
count the environment already declares smaller than that cap stays; the cap never raises it.

`--work <name>` gives the render `build/runtime/work/<name>/` in its repository and, before the
render queues, marks it in `.ethos-owner.json` with the actor that the session declares in
`ETHOS_ACTOR`. A session that names a directory with another owner's mark is refused with
`host_work_owned:<name>` and takes no place in the queue. A session that declares no actor writes
no mark. Remove the directory, or its mark, when the work has ended and its results are kept
elsewhere.

A proof's test gate carries the same mark in its scratch root under the temporary root while the
proof holds a ticket, so a root that outlives an interrupted proof names the session it belonged
to.

## 5. Keep The Guests

- Snapshot a guest before resizing its disk, then resize the disk and the volume inside the guest.
- Prune superseded supply images after a binding keeps the current one; the host store lists what it
  binds.
- Register a runner from the forge's own page, into the runner's own configuration, with the
  `<guest>` account and the `<forge>` group it serves.
- Measure a guest's vCPU count again after any resize, and run the check of section 2 with the new
  number.
