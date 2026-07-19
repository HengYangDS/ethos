## Context

ETHOS already distinguishes Work Lane proof, candidate landing, accepted-root
closeout, and remote publication. The global declarative-compression program
needs many of those local transitions before a coherent dual-remote release,
but its current `transition` budget enforcement permits temporary declared debt
without telling pre-push admission to defer external publication.

## Goals / Non-Goals

**Goals:**

- Make one manifest declaration select campaign-scoped remote publication.
- Keep each Change independently archiveable and locally closeout-able.
- Treat temporary debt as a bounded campaign investment, not a per-Change
  rejection; require terminal budget compliance and no active debt at the
  campaign boundary.
- Reuse the existing campaign reader and pre-push reducer.

**Non-Goals:**

- No remote mutation, provider integration, workflow engine, parallel policy
  store, new dependency, or alternate push hook.
- No weakening of executed-proof, identity, candidate-topology, or protected
  branch admission.

## Decisions

1. **One `publication.mode` declaration.** `campaign_terminal` implies both
   local Change closeout and terminal-only remote publication. Separate
   `allow_local_closeout` / `allow_remote_push` booleans could contradict each
   other and create a second policy state.

2. **Read-model composition, not a new service.** `campaign_report` extends
   each manifest with `publication`; terminal readiness composes existing
   campaign step facts with `source_budget_report`. `push_admission_report`
   consumes that projection only for protected roles.

3. **External declarations own variable facts.** Campaign values remain in
   `campaign.toml`, structure and lifecycle vocabulary remain in
   `campaign.schema.json`, source-budget values and the unique Campaign binding
   remain in `.ethos/rules.toml`, and action commands remain in
   `system/commands.toml`. Python owns generic loading, validation, projection,
   and admission only; it does not own Campaign names, remote topology, or
   action prose.

4. **Terminal means closed campaign, retired/archive-complete steps, terminal
   budget met, and no active debt.** A source-budget terminal target alone
   cannot prove campaign completion, while a closed step list alone could leave
   temporary architecture debt or the global compression target unmet.

5. **Unconfigured campaigns do not change current publication semantics.**
   `publication` is optional in the schema; only a declared
   `campaign_terminal` campaign gates protected remote pushes. This avoids
   silently changing unrelated campaign behavior.

6. **`campaign_terminal` has one external Campaign binding.** The policy must
   declare exactly one `campaign_id`; non-Campaign modes must not declare one.
   The same Pydantic owner generates the published JSON Schema cross-field
   contract so runtime validation and external tooling cannot diverge.

7. **Campaign growth is visible without mechanically stopping local work.**
   Growth above baseline plus declared allowance becomes an explicit
   `source_budget_campaign_growth_overage` advisory. Invalid policy, debt-cap
   overflow, expired debt, and stale debt remain blocking; terminal targets and
   zero active debt remain protected-publication requirements.

8. **Archive-before-land has an honest intermediate state.** `active` and
   `in_progress` require an active OpenSpec carrier. `archived` and `landed`
   require an archived carrier while closeout is still non-terminal. Only
   `closed` and `retired` require terminal closeout heads and evidence.

9. **Publication status is repository-scoped.** Filtering `campaign status` to
   one Campaign does not weaken the repository-wide protected-publication
   projection; the payload labels that scope explicitly.

## Risks / Trade-offs

- **A local hook is bypassable** → the local pre-push hook is defense in depth;
  receiving-plane branch protection and hosted policy remain the authority for
  remote acceptance. This Change claims only local-client admission.
- **Source-budget logic becomes a second campaign truth store** → the campaign
  reader consumes the existing budget report and stores no copied metrics.
- **Invalid TOML is normalized into a harmless default** → every parsed manifest
  is validated against `campaign.schema.json`; any invalid declaration blocks
  protected publication rather than falling through as unconfigured.
- **A second active terminal campaign is declared** → every non-terminal one
  blocks publication; the report names all blockers rather than choosing one
  arbitrarily.

## Migration Plan

1. Add RED tests for manifest parsing, terminal readiness, and protected push
   denial while non-terminal.
2. Extend the external schemas and declarations, then keep the reader and
   pre-push reducer generic.
3. Update campaign closeout guidance and validate formatting, Schema, OpenSpec,
   Claim, focused tests, and local proof.
4. Archive this Change before local candidate/accepted closeout. Rollback is a
   normal revert; no remote operation is part of this Change.

## Open Questions

None. The campaign-wide remote boundary and acceptance criteria are explicit in
the program plan and this Change.
