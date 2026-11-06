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

The gate declarations own check identity, dependency closure, execution
identity and proof-set membership: the [packaged registry](../../system/gates.toml)
for the obligations every repository shares, and the gates a repository's
profile declares or names for its own. Native configuration owns
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

## Forge Projections

Each Forge's CI is a projection of the same gates. The gate declaration and its owner commands compile through `.config/ci/pipeline.cue` into the generated `.github/workflows/ci.yml` and `.gitlab-ci.yml`. Neither generated file is an editable source, and `ethos lane project` writes both from the model (repository-paradigm "CI for several Forges is one model" and "Repository orchestration is native").

A hosted run on a Forge is a separate observation of that Forge's plane (proof-hosts "Hosted provider observations remain evidence-class scoped"). Local proof, hosted status, ref reachability and release publication are distinct evidence states, and none stands in for another (quality "Local And Hosted Planes Stay Separate").

## Dependency Safety

The runner executes the admitted DAG through one bounded ready-node executor.
A completed prerequisite releases its dependents without waiting for unrelated
readers. Ready file-writing gates drain active readers and run alone. Results
retain canonical plan order rather than completion order. Invalid graphs fail
before execution. A dependent gate executes only after every
prerequisite has passed with exit code zero; otherwise it receives an unexecuted
blocked result naming the unmet dependency. Independent diagnostics can
continue. Dry-run projection does not execute effects or invent failed checks.
The declared inexpensive source checks precede heavy tests. Package delivery no
longer waits for coverage (`ecf55c727`); a coverage failure still fails the proof.
These prerequisites belong to the gate declaration, not a second phase registry.

Provider gates call their declared Python owner. Adapter gates invoke their
declared command. Results retain identity, verdict, exit code, diagnostics,
stdout and stderr; they do not infer success from missing evidence.

## Local Fallback Evidence

When no peer is reachable, `ethos publish` falls back to the proof Attestation
it already admits for the head: the proof runs the owner's declared gates.
`local_ci_fallback` reports that admission as `admitted`, `missing`,
`unavailable` or `not_required`, with text, and a missing proof names the full
proof command. The fallback never claims hosted CI success, remote publication
or installed-runtime acceptance. Those claims each need their own current
evidence.

See also: [Command Plane](../reference/command-plane.md) and
[Quality Gate Governance](../../.agents/skills/ethos-quality-gate-governance/SKILL.md).
