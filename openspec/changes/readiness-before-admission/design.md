# Design

## Context

See [proposal.md](proposal.md). `run_gate_graph` (`src/ethos/adapters/gates/runner.py`) already
splits a plan in two through `_scheduled_nodes`. A gate of kind `test` or `package`, and every gate
that depends on one, waits for every other gate, the readiness tier, and `_run_ready_gate` blocks it
with `gate_dependency_not_proven` when one of them failed. `prove` enters `admitted_full_proof`
(`src/ethos/adapters/gates/proof_slot.py`) around the whole graph.

## Goals / Non-Goals

**Goals:**

- A readiness failure ends a full proof before any admission wait.
- A passing proof waits once and runs each gate once.

**Non-Goals:**

- Changing which gates form the readiness tier, or the admission rule, its limit or its bound.
- Cancelling readiness gates that still run when another one fails.
- Focused proofs, which never wait for admission.

## Decisions

- **Reuse the existing tier.** The tier is the one `_scheduled_nodes` already derives from gate
  kinds, exposed once as `readiness_tier(nodes, gates)`. The scheduler and the proof read the same
  set, so they cannot disagree.
- **Two graph runs, one result.** `run_plan_checks` takes an optional admission scope. With one, it
  runs the readiness nodes, then the whole plan with their results as settled input
  (`run_gate_graph(..., settled=...)`). That second run happens inside the admission scope when
  every readiness gate succeeded and outside it otherwise, where every remaining gate is blocked by
  its failed dependency. Settled gates are neither scheduled nor reported again, and one epoch keeps
  every gate's `started_after_seconds` on one timeline, the admission wait included.
- **Readiness runs outside the slot.** Readiness gates are static checks of a committed tree; the
  slot and the load wait protect the test and package gates, which load the host. Two proofs of one
  repository can now run their readiness tiers at once; the slot still serializes their tests.

## Risks / Trade-offs

- [Readiness runs on a loaded host] → It takes about a minute at ETHOS's size. On a busy host it
  may take longer, but it no longer waits first.
- [A readiness gate needs host capacity] → None does today. A gate that needs admission declares
  the kind `test` or `package`, which places it after admission.
