# Design

## Context

See [proposal.md](proposal.md). Design revision 5.3
(`build/runtime/work/architecture-realization/product-architecture.md`, "Concise surface" and
Move 6) names the two definitions and the measured basis. Git's native hook reaches push admission
through `adapters/repo/hook/admission.py` `_pre_push`, which calls the same `push_admission_report`
as the removed command.

Constraints:

- **Layers.** The import contract orders `surface`, `domain`, `adapters`, `repository`; adapters do
  not import the domain tier, so `push_admission_report` cannot reach a builder in
  `domain/land/closeout.py`.
- **Budget.** `python_product` is 69,900 of 70,000 on `dev`. This Change deletes, and the next
  adding Change in the other lane waits for its measured headroom.

## Goals / Non-Goals

**Goals:**

- Every push consumer reports the repair that the removed command composed, from one owner.
- Each removed definition has no remaining product, test, tool or governed-repository consumer.

**Non-Goals:**

- `hook admit` and `lane candidate --materialize`, which have their own entry points and journeys
  (design revision 5.3, measurements 4 and 5).
- Any new requirement: the native pre-push admission requirements already state the obligation.

## Decisions

### 1. The producer names the closeout repair

`push_admission_report` returns the exact accepted-closeout command whenever its gaps include
`accepted_closeout_effect_not_attested`, and the proof's next action otherwise. The native hook, the
publication preview and the publish effect read the same report, so each names the same repair as
`ethos status` and `ethos plan`.

### 2. The closeout command is a recovery command

`closeout_apply_command` moves, unchanged, to `adapters/mutation/remediation/guidance.py`, beside
the proof and archive recovery commands. It resolves the accepted root from adapter facts and branch
roles, so both the land reducers and push admission reach it within the layer contract.

Alternatives rejected:

- A pure command builder in `guidance.py` with root resolution left to each caller. Two callers
  would each own the accepted-root resolution.
- A function-level import of the domain builder. The layer contract reads every import.

### 3. Tests exercise the producer

The tests that ran the CLI copy call `push_admission_report` with the coordinates that the native
hook passes, and assert the same verdicts, gaps and next actions. The retired-surface regression
expects `Unknown command` for `ethos hook pre-push`.

## Risks / Trade-offs

- [A caller relied on the hidden command] → No product, test, tool or governed repository invokes
  it; Git's hook and `push_admission_report` keep the admission and its report.
- [The push report's next action changes] → It changes only for
  `accepted_closeout_effect_not_attested`, to the command that status and plan already name; the
  shared-command regression holds the four equal.
- [The recovery module gains adapter imports] → It imports status and branch-role readers that do
  not import the mutation tier, and `lint-imports` keeps the layer contract.
