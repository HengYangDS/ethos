# Design

## Context

See the [proposal](proposal.md). `repository_paradigm_report` in
`src/ethos/repository/paradigm/report.py` collects every obligation's gaps into one list and
derives `required_gaps` from all of them; `close_verdict` turns a pass with required gaps into a
block, the repository audit reduces over the report, and proof and landing refuse while the audit
blocks. `src/ethos/adapters/repo/hook/staged_text.py` refuses a staged package marker without a
docstring on its own path, apart from the audit. The paradigm declaration has no row per
obligation: an obligation is a name that a gap carries.

DR-0027 and the archived common-base plan both describe a rule's lifecycle as report, refuse new,
then arm, and both plan its mechanism for later Changes. This Change does not build that
mechanism.

## Goals / Non-Goals

Goals:

- The package-docstring obligation stops blocking proof, landing and commits, in the audit and in
  the hook, and its gaps stay visible with their repair.
- The state lives in the paradigm declaration, read by both enforcement points, so arming an
  obligation is an edit of that declaration.

Non-Goals:

- The obligation's scope: which markers owe a docstring. The owner has not ruled on it.
- The release in which the obligation arms again, and any repair verb or reach preview for it.
- The "refuse new" stage, a per-repository state or a dated arming: later Changes own the
  lifecycle and replace this list with their carrier.
- Any other obligation. Each is armed today and stays so.

## Decisions

1. **One list in the declaration.** `reporting` in `src/ethos/contracts/paradigm/paradigm.toml`, a
   field on the model with an empty default. A list is the smallest carrier, and the paradigm has
   no obligation rows to hold a state field yet. It holds `package-docstring`, which the owner
   ruled on, and `identifier-source`, which this batch ships for the first time: an obligation
   absent from the list is armed only if it shipped through beta.10. The audit's semantic closure
   is the one other finding that does not block; it keeps its own path until rules have rows.
2. **The report keeps every gap and requires only the armed ones.** `gaps` still lists each gap
   with its obligation, carrier and repair; `required_gaps` holds the armed ones; the new
   `reported_gaps` holds the rest by their stable identity. The next action is computed from the
   armed gaps, so a repository whose only gaps report is told nothing to do.
3. **One reader, two callers.** The declaration's `armed(obligation)` is the only reader of the
   list. The report's closure calls it for every gap, and `pre-commit` calls it for the package
   marker check: while the obligation reports, a staged marker is not checked, and the code path
   and its gap name stay for the day it arms. A third enforcement point would call the same
   function.
4. **The words are reporting and armed.** `report_only` already names a gap that the repair plan
   cannot write and stays as it is.

## Risks / Trade-offs

- A reporting gap is easy to ignore: no command routes to it. That is the decision's intent until
  the scope is ruled; the counts stay readable in `ethos status`.
- `lane repair-paradigm` still lists the markers among the gaps it cannot write, since it reads
  the report's full gap list. Its verdict was and stays a pass.
- A later lifecycle Change must migrate this list. It is one key with one entry.
- Two governed repositories are unblocked only when they bind the release that carries this
  Change; their other required gaps are unchanged.
