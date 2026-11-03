# Design

## Context

See [proposal.md](proposal.md). `run_plan_checks` in `src/ethos/surface/cli/root/proof.py` runs the
readiness tier of a full executing proof, then enters the admission scope, which holds the
repository's proof slot and waits for the 1- and 5-minute load averages to fall within the limit,
and runs the whole plan inside it with the readiness results already settled. Admission protects the
test and package gates, whose workers fail by timeout on a loaded host.

## Goals / Non-Goals

**Goals:**

- A full proof waits for admission only when it still has a gate to run after its readiness gates.

**Non-Goals:**

- Changing the load limit, the admission bound or the order in which gates run.
- Admitting a proof that plans a test or package gate without the wait.

## Decisions

- **Admission follows the remaining plan.** After the readiness tier passes, the proof enters
  admission when any planned gate lies outside that tier, as before; when none does, every gate has
  run and the proof finishes without the slot or the load wait, and its result records no admission.
  The readiness tier is the existing definition, so the condition adds no gate classification.

## Risks / Trade-offs

- [Two readiness-only full proofs of one repository run at once] → They run light gates, and the
  slot never protected attestation writing, which follows the gate run in both cases.
