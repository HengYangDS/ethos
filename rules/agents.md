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
- Apply the feedback closure below to repeated failures and accepted guidance.
  A bounded implementation does not narrow a global requirement.
- Before prose writes, select the existing semantic owner and lifetime from the
  Product Design Contract. Distinguish obligations, rationale, observations, and
  completion claims; update their owner or reference exact evidence rather
  than copy an execution narrative into the current file. External method-pack
  templates do not override this allocation.
- Before freezing an atomic HEAD, review the diff for carrier responsibility,
  preserved obligations, duplicate meaning, and evidence binding. Format,
  schema, and test success do not establish prose's semantic compliance. Keep
  proof results in their existing Attestation or receipt, not in a result-only
  source edit that creates another proof obligation. A task checkbox is never
  a substitute for the executable exact-current proof precondition.
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

## Feedback Closure

Learning changes an effective owner and demonstrates the resulting behavior;
an acknowledgement, retrospective, checkbox or added document is not closure.

1. Preserve the source's scope and distinct obligations in the existing official
   Change. An example may illustrate a global rule; do not replace that rule
   with the example or silently discard obligations outside the current batch.
2. Resolve each obligation as an implemented improvement, an already-satisfied
   requirement with current evidence, a justified supersession or rejection,
   or an explicitly open gap. An unverified claim stays open.
3. Diagnose the failed assumption and responsible producer, consumer and trust
   boundary. On recurrence, test why the existing rule, skill, check or recovery
   failed; do not add the same local workaround again.
4. Change the unique owner: executable behavior or native policy for decidable
   constraints, rules for stable boundaries, skills for reusable procedure, and
   docs for explanation or decisions. Other carriers reference that owner.
   Updating every layer or creating a new skill is not inherently necessary.
5. Define the observation that distinguishes the former failure from the
   intended result. Exercise the actual consumer, including relevant denial,
   unknown and recovery paths. Bind evidence to the tested source, policy,
   environment and effect; retain limitations and remove replaced bypasses.
6. Close only the demonstrated scope in official tasks. Missing or contradictory
   evidence reopens the affected acceptance. Installation, host activation,
   publication and use remain separate claims when the requirement includes them.

Skills guide these decisions; their presence does not enforce them. Machine
checks must consume explicit accepted obligations and real execution evidence,
not infer improvement from prose headings, file counts or test totals. Unrecorded
conversation and the adequacy of an interpretation cannot be certified by a
structural gate. Do not create a feedback database or second progress ledger.
