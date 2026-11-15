# Design

## Context

`admitted_host_work` in `src/ethos/adapters/gates/host_admission.py` takes a place in the host
queue, waits until the queue admits it, yields the admission and leaves. It has two consumers:
`run_admitted`, which is `ethos host run`, and `_admitted_gates` in
`src/ethos/application/proof/host.py`, which is the executing host proof. The full proof does not
use it: `admitted_full_proof` holds a `HostPlace` itself, and its own `finally` covers its wait.

In 0.2.0-beta.10 the function left the queue in one `finally` around the wait and the admitted
body. The commit `a20bbaa3e` wrapped the wait in a translation of OS errors to
`host_admission_unavailable` and kept the `finally` around the body alone. A wait that ends
without admission therefore keeps the ticket that its first poll took.

Measured on the base with the three regressions of this Change, run with the bounded pytest
command on `tests/unit/gates/test_host_admission.py`: after each exit the queue's read lists the
run's ticket behind the holder, and a later arrival of the same process is refused with
`host_admission_contended` naming the leaked ticket's own operation. A second measurement dropped
the raised error: the ticket was still listed, and it went only after a collection by the
interpreter, when the lock library's finalizer released the lock. The record and the lock file
stayed in both measurements, for the next waiter to remove. Through the host proof's own command
the ticket was no longer live when the command returned: a temporary assertion on the queue,
placed in the contended host proof's test ahead of its assertions on the result, passed at the
base. So the live ticket lasts as long as the abandoned wait stays uncollected, not as long as
the process.

The host proof runs its readiness tier before it asks for the ticket. A refused admission leaves
`_admitted_gates` as a `ValueError`, which `observe_gate_execution` reads into the result's gap.
The readiness results are local to `_admitted_gates` at that point, so the result holds no check.
`observe_gate_execution` is pinned at a decision density of 21 in
`tests/fixtures/decision-density-baseline.json` and may not grow.

## Goals / Non-Goals

Goals:

- A wait that ends without admission leaves no ticket, record or lock file of its run.
- A host proof whose admission is refused reports the readiness results that ran and names the
  gates that did not run.

Non-Goals:

- The full proof's result when its admission is refused. It drops its readiness results in the
  same way, through another function; the draft Change `focused-proof-result` owns that class.
- Whether a host proof whose readiness gate failed should ask for the ticket at all.
- A new gap code, a new option or a change to the verdict, the gap or the exit of a refusal.

## Decisions

1. **The release is registered once, as soon as the place exists.**
   - **Rests on:** the three failing cases of
     `test_a_wait_that_ends_unadmitted_gives_up_its_place` at the base, and the released form read
     with `git show v0.2.0-beta.10:src/ethos/adapters/gates/host_admission.py`.
   - **Considered:** one `finally` around both parts, as released, which now needs a guard for a
     place that was never built, because building the place moved inside the translation of OS
     errors; a release at each of the three exits, which a fourth exit would miss again; and
     making the place a context manager, which also changes the full proof's consumer.
   - **Chosen because:** one exit stack around the wait and the body runs the release on every
     exit, an interrupt included, and adds no decision. The function's density is 6 before and
     after, measured with `complexipy` in the clone. The trade-off is one more level of
     indentation in the function.
   - **Applies to:** `admitted_host_work` and both consumers. A run that joined a live admission
     took no ticket, so its release does nothing, as before. `admitted_full_proof` is not changed.
2. **The refusal carries what ran.**
   - **Rests on:** the three regressions of a refused host proof, each failing at the base on
     an empty `data.checks`, and the pin of `observe_gate_execution`, which measures 21 before
     and after.
   - **Considered:** a third return value from `_admitted_gates` or a second `except` clause in
     `observe_gate_execution`, each of which adds a decision to a function at its pin; running the
     readiness tier in `observe_gate_execution`, which moves the tiering to the caller; and a list
     that the caller passes in to be filled, which hides an output in a parameter.
   - **Chosen because:** the failure already travels as an error to the one place that builds the
     result. A private subclass of the outcome error keeps the refusal's decision as it was read
     and adds the readiness results and the names of the other gates; one helper of density 3
     chooses what a failure keeps.
   - **Applies to:** every refusal of the admission in a host proof: the bound, an unwritable
     queue, an absent host root and an invalid declaration, which all leave the same statement.
     Regressions exercise the first three; the invalid declaration takes the same statement
     and is read in the code, not run. Any other failure keeps the checks it had and names no
     gate, because what it ran is not known.
3. **The result names the gates in `data.not_run`, only when there are any.**
   - **Rests on:** the readiness run's result, which already names its unrun gates in a field of
     this name.
   - **Considered:** the field in every host result, empty when all ran, which changes the shape
     that every reader of a host proof sees; the field in the summary too, which an existing test
     compares whole; and one `gate_missing` gap for each gate, which adds gaps to a refusal that
     has one cause.
   - **Chosen because:** it is the smallest change of shape and reuses the name a reader knows.
   - **Applies to:** the host proof's `data`. `data.executed` is true and `summary.gate_count`
     counts the readiness gates, because both derive from the checks the result holds.

## Risks / Trade-offs

- A reader that took `data.executed: true` to mean that every selected gate ran now sees it on a
  refused host proof. The verdict stays `block` with the admission's gap, and `data.not_run`
  names the rest.
- A release that itself fails, for example on a record it cannot remove, now ends a refused wait
  with that error in place of the refusal. The admitted body already behaved so.
