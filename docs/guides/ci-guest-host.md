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
- `slots` is how many heavy runs may share the host; one is the default.

`ethos host status --guest-cpus <N>` reports whether `N` fits inside `reserved_cpus` and answers
`host_reservation_exceeded` when it does not. It removes nothing and names no repository path.

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

## 4. Run A Render

```bash
ethos host run -- <render command>
```

The render takes its place in the queue and receives `ETHOS_HOST_CPU_CAP` and
`PYTEST_XDIST_AUTO_NUM_WORKERS`: the CPUs that the declaration leaves. A worker count the environment
already declares smaller than that cap stays; the cap never raises it.

## 5. Keep The Guests

- Snapshot a guest before resizing its disk, then resize the disk and the volume inside the guest.
- Prune superseded supply images after a binding keeps the current one; the host store lists what it
  binds.
- Register a runner from the forge's own page, into the runner's own configuration, with the
  `<guest>` account and the `<forge>` group it serves.
- Measure a guest's vCPU count again after any resize, and run the check of section 2 with the new
  number.
