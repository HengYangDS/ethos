# Design

## Context

See [proposal.md](proposal.md). GitLab issue #2 asked for one gap code in one place. The owner
asked on 2026-11-05 for the essential fix instead of site patches. A draft went to a compatibility
review and a product review, and both approved it with conditions. This design records the decision
and those conditions, because the draft lives in the ignored `build/` directory.

The reviews found the defect in these places:

- the proof reducer, which replaces a cause with a class code;
- the issuance boundary, which always emits `block`;
- the gate runner's dependency skip and its host observation;
- the shared process and public-contract boundaries;
- status, Work Lane refresh, retirement and commit creation;
- about thirty single-gap transports in five forms: `raise`, `_fail`, `require_release`,
  `_require` and a native process's message.

Land and publish already conform. Publish passes on the next actions its parts declare.

## Goals / Non-Goals

Goals:

- One kernel value and one composition rule that every aggregator and boundary uses, so a new
  aggregator cannot lose a cause by accident.
- A timed-out gate reaches the top-level result as `gate_timeout:<gate>` with verdict `unknown`.

Non-goals:

- New gap codes, a remedy registry, or new fields in stored statements or checks.
- Changing which results authorize an effect: only `pass` does, before and after.

## Decisions

1. **Kernel `Outcome`.** It holds:
   - a verdict;
   - ordered, deduplicated gaps;
   - bounded cause records;
   - a next action.

   `Outcome.part` builds one non-pass part. It puts the class code first, then at most five of the
   part's own codes, and records the subject, kind, verdict, codes and an omitted count. `combine`
   reduces the verdicts with `reduce_verdicts` and never infers a verdict from the presence of
   gaps; only `Outcome.of` closes a declared `pass` that carries gaps, as the kernel already
   requires.

2. **One error.** `OutcomeError(ValueError)` carries an `Outcome` and an optional observation, and
   its message is the leading gap. Existing handlers that read `str(error)` behave as before.
   - `ProcessExecutionError` becomes an `OutcomeError`. Its producer declares the verdict class: a
     Git timeout is `unknown`.
   - `outcome_of(error)` reads the carried value, or a single `block` gap for any other error.
3. **One conversion.** `EthosResult.from_outcome` builds every boundary's result.
   - `_emit_proof_gap` keeps the `gapped` state and its exact stale-base continuation.
   - Process failures keep their Git-specific continuations.
   - Public-contract failures keep `_contract_failure_action` for the leading gap.
4. **Proof.**
   - The kernel's `gate_outcome(checks)` builds one part per executed non-pass check. Its class
     code is `gate_failed:<gate>` or `gate_unknown:<gate>`, followed by the gap codes from the
     check's diagnostics. The record keeps the leading diagnostic's kind, timeout and elapsed
     seconds, and the check's exit code and duration, the facts that survive check normalization.
   - `assess_proof_execution`, issuance and the host observation all use it. Issuance raises an
     `OutcomeError` carrying the assessed verdict, the gaps and the causes.
   - The next action of a gapped proof is the first remedy that `remediation_for_gaps` returns for
     its gaps, otherwise `ethos plan --changed --json`. That function gains remedies for
     `gate_timeout:` and `missing_command:`.
5. **Dependencies.** A gate that does not run because a prerequisite did not pass takes
   `reduce_verdicts` over its unmet prerequisites. A prerequisite that claimed `pass` without exit
   code zero counts as `block`.
6. **Invariants from the compatibility review.**
   - The reduction covers executed parts only, so dry-run `prove` output stays byte-identical and
     the predecessor probe still sees only `full_proof_requires_execute`.
   - Stored statements keep `_STATEMENT_FIELDS`, and checks keep their shape. Passing checks gain
     nothing.
   - The exact matchers in `surface/cli/root/proof.py` and `adapters/admission/ref_move_policy.py`
     keep their behaviour.
7. **Vocabulary.** The result for a gate that the plan does not declare becomes
   `gate_undeclared:<gate>`, so `gate_unknown:<gate>` means only a gate whose verdict is unknown.
8. **Ratchet.** An architecture test refuses `<x>gaps[0]` as an argument to an error constructor,
   or to a failure helper named `_fail`, `_require` or `require_*`, in product code.

## Risks / Trade-offs

- Result lists get longer for non-pass results. Every class code stays first, so prefix matches
  keep working.
- A timed-out proof moves from `block` to `unknown`, and a dependent of an unknown gate does too.
  Both stay non-pass and keep exit status 1, so only scripts that match `block` exactly notice.
- The five-code bound can hide a cause. The diagnostic counts what it omits, and the proof
  artifact keeps every diagnostic.
- `create_git_commit` returns Git's own failed process, as before, but a created object that the
  commit policy refuses raises a refusal with every gap instead of returning a process whose
  standard error is the first gap. Its three callers keep their class code first and append the
  refusal's gaps. The ratchet also refuses a `CompletedProcess` built from a first gap.
