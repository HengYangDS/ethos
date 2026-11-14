# Design

## Context

See the [proposal](proposal.md). One queue holds every heavy local run of a host, and entries write
a ticket named by arrival time, pid and nonce whose OS lock proves the holder lives
(`src/ethos/adapters/gates/host_admission.py`). A governed full proof enters it through
`admitted_full_proof`, and `ethos host run` through `run_admitted`; a host proof skips it. A ticket
records its repository's absolute path, and every output that names a holder prints that path. The
host declaration takes exactly `slots`, `reserved_cpus` and `load_limit`, and every release from
0.2.0-beta.2 to beta.9 refuses a declaration with an unknown key. Ledger rulings of 2026-11-14 fix
the read's input, the ticket-only proof, the owner mark's visibility, the gap's suffix and the
split.

## Goals / Non-Goals

Goals:

- A foreground host proof holds the host ticket while its test and package gates run, and its result
  records the wait and whether it joined.
- One catalog read lists the declaration, the queue and its holder, and prints no repository path.
- The guests' virtual CPUs are checked against `reserved_cpus`.
- A tracked runbook covers a host that runs CI guests.

Non-Goals:

- No guest joins the queue, and ETHOS reads no hypervisor.
- No new key in `host.toml`, and no load wait for a host proof: the ticket decides, and an idle
  proof's start under load stays the `load_limit` rule it is today.
- No yielding class and no owner-marked scratch: those are the separate rows `host-yielding` and
  `scratch-owner-mark`.
- No security boundary between two processes of one user.

## Decisions

1. **A host proof takes the ticket for the gates after readiness.** `observe_gate_execution` splits
   its plan as the governed proof does: the readiness tier runs first without waiting, and every
   other gate runs inside `admitted_host_work` with the environment exported. A plan of readiness
   gates alone never waits, and a live admission is joined rather than taken again, so a host gate
   inside an admitted full proof does not wait for itself. The rule follows the gate's kind, not
   the flag, because a full proof's readiness tier runs focused host proofs.
2. **Ticket only.** No repository slot and no load wait. The load limit that governs an idle
   proof's start is unchanged: it is the host's declaration, and an explicit
   `ETHOS_PROOF_HOST_LOAD_LIMIT` is recorded with its source so that an override is visible. This
   Change neither refuses nor endorses the variable; the ticket decides the queue at any load.
3. **A ticket names its operation and owner; results print no path.** The record adds `operation`
   and `owner` and keeps `repository`, `executable` and `since`, because the released engines that
   adopters still select drop a record without those three. One projection carries the operation,
   the executable, the owner mark, the pid from the ticket's name, the start time and
   `same_repository`; the owner mark is blank unless the reading repository shares the holder's Git
   common directory, and the gap names the operation, or the executable of a record that has none.
4. **The worker cap only lowers.** `HostPlace.environment` keeps a smaller positive
   `PYTEST_XDIST_AUTO_NUM_WORKERS` that the caller already declares, so a guest with more CPUs
   cannot raise the worker count of the job it hosts.
5. **`ethos host status` is the one read.** It is the operation `host.status`, effects `read`, exit
   `observe`, beside `host.run` in the same module. It returns the declaration with the limit's
   source, the 1-minute load and every live ticket in arrival order with `holding` or `waiting`; it
   removes nothing, because the read must not race an entrant.
6. **The reservation is `reserved_cpus`; the guests' count is an input.** `--guest-cpus N` reports
   whether `N` fits and answers `host_reservation_exceeded` when it does not, and
   `host_reservation_invalid` below zero. It is not a declaration key: every released engine with
   the queue refuses an unknown key, which would stop the full proofs of each repository still on
   one, and the hypervisor's own guest configuration owns the number.
7. **The runbook is `docs/guides/ci-guest-host.md`.** It sizes the declaration against the guests,
   runs the check, reads the queue, and runs renders under `ethos host run`, with no guest address,
   token value or host name.

## Risks / Trade-offs

- [A CI runner whose host root cannot be written now fails a host proof that passed] → It answers
  `block` with `host_admission_unavailable`; the lane's hosted runs show the root is writable.
- [Engines of several releases share one queue] → Ticket names, locks and the three old fields are
  unchanged; an older engine's record has no operation, so the gap names its executable.
- [The gap's suffix changes] → A breaking diagnostic with the stable code kept, stated in the
  changelog.
- [A host proof holds the only slot for a long time] → The read names it, and the wait is bounded.
- [The owner mark of another repository is hidden] → Accepted: a repository's result never
  discloses another repository's private detail, and `same_repository` says the rest.
