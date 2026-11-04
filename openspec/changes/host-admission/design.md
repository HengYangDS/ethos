# Design

## Context

See [proposal.md](proposal.md). `admitted_full_proof` in `src/ethos/adapters/gates/proof_slot.py`
holds a `FileLock` in the repository's local state root and polls the 1- and 5-minute load until
both fall within half the CPUs, for at most `admission_seconds`. AIGW and Proxy reviewed the design
on 11-04 (`build/runtime/work/iteration-speed/host-admission-draft.md`).

## Goals / Non-Goals

**Goals:**

- At most `slots` heavy local runs at a time on one host, served first come, first served.
- One declaration that GUI-launched agents, launchd jobs and ETHOS's tool-only environment all read.
- A bounded wait whose gap names who holds the host.

**Non-Goals:**

- Stopping a CI guest, or lowering any process's priority.
- An unbounded wait, a load limit derived from the reservation, or admitting a command's children
  one by one.

## Decisions

- **A queue of owned tickets.** A waiter writes a ticket named by its arrival time, pid and nonce in
  `<host root>/host-admission/v1/`, and keeps an OS lock on it for its lifetime. It is admitted when
  fewer than `slots` live tickets precede its own. Testing another ticket's lock tells live from
  dead, so a crashed holder needs no cleanup by age. An advisory lock alone cannot serve waiters in
  order.
- **The ticket records no arguments.** It holds the repository, the executable's name and the start
  time. A command line can carry secrets, and the wait's gap needs only those three.
- **The host root owns the declaration.** `host.toml` sits in `host_store_root()`, which every
  platform already resolves. Shell variables do not reach GUI-launched agents or launchd jobs, and
  ETHOS strips its tool environment.
- **Nested work is admitted once.** The holder's child receives `ETHOS_HOST_ADMISSION` with its
  ticket's nonce and pid. Nested work joins only while that ticket is live and held by that pid, so
  a copied variable admits nothing.
- **The reservation bounds workers, not the load gate.** Load already counts busy virtual machines,
  so also subtracting their reservation would count them twice.

## Risks / Trade-offs

- [A long render holds the host for its whole run] → The wait is bounded and its gap names the
  holder; one admission wraps one render, not a chain.
- [Windows has no load average] → Admission records the load as not measured instead of passing
  silently, and the slot still serializes.
- [An older pinned engine ignores the protocol] → Only engines from this release take the slot, so
  the 7-day acceptance starts when every repository runs it.
- [Admitted heavy work still starves the CI guests, which cannot take the host slot] → On 11-04,
  architecture-publisher's GitLab job 65187 hit its 30-minute timeout during a full-core render. The
  same job took 1,278 s in the morning. `reserved_cpus` keeps CPUs for the guests only from children
  that honor `ETHOS_HOST_CPU_CAP` or `PYTEST_XDIST_AUTO_NUM_WORKERS`, so a render tool must read
  the cap itself.
- [Busy guests keep the host's load above half its CPUs] → `host.toml` declares `load_limit`, and
  admission reads two calm 1-minute samples, not the lagging 5-minute average. On 11-04, a
  60-second proof waited 51 minutes at limit 9 while three guests held about 8 CPU-equivalents.
