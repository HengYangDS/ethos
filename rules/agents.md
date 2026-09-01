# Agent Rules

Purpose: define how agents load repository truth and avoid stale context.

| Field | Rule |
| --- | --- |
| Authority | [Product Design Contract](../docs/governance/product-design-contract.md), `ethos status --json` |
| Trigger | Starting work in this repository or crossing into this repository from another root. |
| Action | Load `AGENTS.md`, observe current status, obey the current result, then expand only into the selected owner. |
| Evidence | `ethos status --json` reports the target root, branch role, decision, gaps, and continuation. |
| Stop | Target path belongs to a different Git root whose `AGENTS.md` has not been loaded. |

## Rules

- Recompute repository root before acting on absolute paths.
- Do not reuse context from another repository after the target path changes.
- Treat host-local memory, IDE state, generated views, and chat output as
  context only. They cannot authorize product behavior, mutation, proof,
  retirement, or completion.
- For broad feedback recovery, declare one finite source boundary in an
  official OpenSpec Change. Preserve distinct semantic obligations rather than
  message count; classify each as accepted, superseded, pending verification,
  or rejected; and move accepted meaning to one existing owner. Do not create a
  feedback ledger, registry, second roadmap, or memory-backed product truth.
- Separate delegated material into observed fact, inference, and proposed
  remedy. Verify observations against current repository or runtime facts and
  never admit the proposed mechanism merely because the observation is valid.
- A later direct instruction supersedes an earlier instruction only on the same
  subject. Contradiction or missing evidence remains explicit and authorizes no
  guessed mutation.
- Use progressive disclosure: load the entrypoint and current status first,
  then only the rule, skill, OpenSpec Change, or direct reference selected by
  the task and current result. Do not bulk-load unrelated docs, archives,
  generated artifacts, evidence, or every skill unless the task is a broad
  audit.
- Treat the schema-versioned result as the current control projection. Agent
  guidance does not own or replay repository lifecycle.
- Before non-trivial governance design, rule, skill-system, hook, scaffold,
  release, evidence, or product-shape mutation, verify the dedicated OpenSpec
  change with `openspec status --change <change> --json`.
- Use repo-local skills from `.agents/skills/` when activation matches.
- Use official external skills as method packs; do not vendor their runtime
  instructions into repository truth.
- Repeated failures must improve the narrow existing owner: product behavior and
  its regression test, an executable rule, or an already-admitted reusable
  skill. Do not create a skill solely to restate product truth.
- Keep one writer for an authority surface. Do not dispatch another agent unless
  the user or current procedure authorizes it and the delegated scope is
  disjoint, bounded, and ownership-safe.
- Optimize verified semantic transitions rather than command count. Reuse fresh
  evidence until its inputs change, stop repeated broad scans, and run heavy
  proof only at a frozen atomic boundary.
- External method packs and execution runtimes may consume OpenSpec and ETHOS
  contracts, but may not create repository-local plan, task, progress, report,
  or lifecycle authority. OpenSpec alone owns Change intent, design,
  specifications, and task progress; Commitment is transient compilation;
  runtime checkpoints belong only in declared disposable runtime homes.
- Before creating, moving, renaming, splitting, importing, or deleting Python,
  read `rules/module_layout.md` and run the module-layout owner gate. Do not use
  file count, directory width, or ELOC as authority for a semantic boundary.
