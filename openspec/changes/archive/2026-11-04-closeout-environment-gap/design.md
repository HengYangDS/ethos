# Design

## Context

See [proposal.md](proposal.md). `compile_gate_policy` adds `gate_runtime_missing:repository-python`
to a policy whose gates run a Python module when no repository Python exists, and the policy's
digest includes its gaps. A passing proof never carries that gap, so a policy compiled where the
runtime is missing can never match a passing proof.

## Goals / Non-Goals

**Goals:**

- Admission names a missing repository runtime as the cause.
- Its report tells the operator how to restore the runtime.

**Non-Goals:**

- Changing what the compiled policy contains, or its digest.
- Letting admission pass without the runtime the committed policy requires.
- Changing the next action that status, plan, closeout and the hooks share.
- Creating the candidate worktree's environment automatically.

## Decisions

- **Runtime gaps come before the floor comparison.** When a policy that admission compiles carries
  a `gate_runtime_missing:` gap, admission returns those gaps without evaluating candidates. No
  passing proof can match such a policy, so the verdict is unchanged; only its cause is named.
- **The repair is a remediation hint.** The existing `remediation_for_gaps` table gives the hint
  `repository_runtime_missing`: run the repository's bootstrap verb in the admitted worktree, then
  retry. The paradigm exposes `bootstrap` through the locked toolchain owner, so the hint names the
  verb rather than one tool's command line. The shared next action stays the retried command, as
  for the table's other hints.

## Risks / Trade-offs

- [A root whose policy has a runtime gap no longer reports other admission gaps] → No passing proof
  can be admitted there before its runtime is restored, and the retry after the bootstrap verb
  reports any remaining gap.
