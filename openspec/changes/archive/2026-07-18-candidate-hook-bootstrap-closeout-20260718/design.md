## Context

A tracked hook has two roles: it is source promoted with the candidate, and it
is executable policy consulted before that promotion commits. When the hook
changes, asking the incumbent file to interpret the candidate's repaired
release-mirror transition creates a bootstrap loop.

## Goals / Non-Goals

**Goals:**

- Use the exact clean candidate hook source only for the official atomic CAS
  that promotes a candidate replacing that tracked hook.
- Preserve the accepted root as the Git transaction root and keep candidate
  semantic admission bound to the candidate head.
- Fail closed if the candidate hook is missing or non-executable.
- Make hook rejection distinguishable from actual ref concurrency.

**Non-Goals:**

- Do not globally rewire `core.hooksPath`.
- Do not provide any process or environment escape hatch for raw Git.
- Do not infer any remote, forge, or release result.

## Decisions

1. `_atomic_update` compares the candidate and accepted
   `reference-transaction` blobs. Only a difference selects Git with a
   command-local `-c core.hooksPath=<candidate>/.githooks`; unchanged-hook
   closeouts retain their existing configured hook route. The scope is one
   official `update-ref --stdin` process; no repository configuration is
   mutated.
2. When the candidate replaces that hook, preflight requires the candidate
   `reference-transaction` file to exist and be executable. The transaction
   cannot proceed unguarded or silently select an alternate hook in that
   replacement case.
3. The candidate-external control-replacement receipt remains required by the
   existing closeout command for changed hook/control paths. The override is not
   an alternate admission route; it selects the exact reviewed candidate hook
   for the same one-shot intents and semantic checks.
4. On an atomic update error, ETHOS reads the accepted and release refs. It
   reports concurrent advancement only when the accepted ref actually departed
   its captured value; otherwise it reports a rejected transaction with stderr.

## Risks / Trade-offs

- Candidate hook source is executed before it becomes accepted source. This is
  deliberate but bounded: the candidate must be clean, at the promoted head,
  proof-bound, and externally receipted when its control paths differ.
- When a candidate replaces the hook, a missing hook must block rather than
  use the incumbent hook, because silent fallback could recreate the bootstrap
  defect or run unguarded. The absence of any hook change retains the existing
  configured-hook lifecycle rather than imposing new scaffold requirements.
- The transaction remains atomic; the override neither splits `dev`/`main` nor
  changes their compare-and-swap values.
