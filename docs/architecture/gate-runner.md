---
subject: ethos:gate-runner
role: explanation
state: canonical
relations:
  canonical_for: proof execution
---

# Gate Runner

Status: canonical execution contract; current verification results are separate
HEAD-bound observations, not this document's state.

Purpose: explain selection, execution safety and the limits of local evidence.

The [gate declaration](../../system/gates.toml) owns check identity, dependency
closure, execution identity and proof-set membership. Native configuration owns
each tool's rules and supply. The policy compiler binds those materials; the
shared runner executes the resulting graph. Local CI uses that same full
closure rather than maintaining a second scheduler or list.

## Readiness And Execution

Run from the intended worktree with its locked environment provisioned and the
invocation actor projected into the process:

```sh
ethos prove --json
ethos prove --execute --gate repository-audit --expect-head "$(git rev-parse HEAD)" --json
ethos prove --execute --full --expect-head "$(git rev-parse HEAD)" --json
```

The first command observes readiness, not execution: planned checks remain
unknown with no exit code. Full proof requires `--execute`. Executed proof
requires the complete selected result set, successful execution and current
source/policy bindings; process success alone cannot establish acceptance.

The default proof set selects offline source checks. Full proof and local CI
also select declared carrier, security and package checks. Some require network
access for provisioning or external freshness. Missing supply or an unavailable
required observation does not pass. Hosted CI is a separate post-publication
observation, not an in-flight pipeline waiting on itself. Read the declaration
for current membership instead of copying gate lists here.

## Dependency Safety

The runner executes the admitted DAG through one bounded ready-node executor.
A completed prerequisite releases its dependents without waiting for unrelated
readers. Ready file-writing gates drain active readers and run alone. Results
retain canonical plan order rather than completion order. Invalid graphs fail
before execution. A dependent gate executes only after every
prerequisite has passed with exit code zero; otherwise it receives an unexecuted
blocked result naming the unmet dependency. Independent diagnostics can
continue. Dry-run projection does not execute effects or invent failed checks.
The declared inexpensive source checks precede heavy tests. Coverage therefore
cannot fail and still launch dependent package delivery. These prerequisites
belong to the gate declaration, not a second phase registry.

Provider gates call their declared Python owner. Adapter gates invoke their
declared command. Results retain identity, verdict, exit code, diagnostics,
stdout and stderr; they do not infer success from missing evidence.

## Local Fallback Evidence

```sh
uv run --frozen --offline python -m nox -s local_ci
```

The outer command selects the locked Python environment; it does not assert
that every selected check is offline. Local fallback requires clean committed
source. It binds HEAD, source overlay and policy, rejects missing, duplicate or
mismatched execution results, and checks source stability before finalization.
The existing fallback receipt is replaced with a non-passing running record
before checks start, so interruption cannot leave an earlier success as this
run's result. An incomplete record does not assert that a child is still alive.
Final logs retain each check's output.

This receipt is local diagnostic evidence, not a proof Attestation, hosted CI
success, remote publication or installed-runtime acceptance. Those claims each
need their own current evidence.

See also: [Command Plane](../reference/command-plane.md) and
[Quality Gate Governance](../../.agents/skills/ethos-quality-gate-governance/SKILL.md).
