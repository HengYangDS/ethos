## Context

ETHOS already exposes product packages, OpenSpec shape/deep validation, claims
digest checks, Work Lane admission, an action graph proof runner, and adopter
parity reports. The incomplete part is semantic composition: those mechanisms
can pass independently without proving that one trust-bearing repository change
has moved from claim through contract delta, execution, evidence, decision, and
promotion.

The target design keeps ETHOS provider-neutral. OpenSpec remains official CLI
surface and specification projection. Work Lanes remain local execution
ownership. Intake and Backlog remain projection or adopter-specific intake.
Claims and repository proof own trust admission, and current source, tests,
docs, canonical specs, or dated evidence carry promoted truth.

## Goals / Non-Goals

**Goals:**

- Make `ethos prove --json` a readiness command unless gates are executed.
- Make `ethos prove --execute --json` and `ethos prove --full --execute --json`
  produce executed evidence that can support promotion.
- Add product trust review that reports a machine-readable envelope for active
  claims and their OpenSpec, evidence, fallback, kill signal, and promotion
  carriers.
- Add OpenSpec lifecycle review that distinguishes valid shape from complete
  change lifecycle and archive readiness.
- Keep adopter-specific rules, including adopter adopter-domain storage parity, in profiles and
  parity evidence instead of ETHOS core semantics.
- Make scaffolding, docs, schemas, and tests cover the full governance skeleton.

**Non-Goals:**

- Do not vendor OpenSpec or replace its CLI semantics.
- Do not move adopter-specific adopter-domain storage or reference-adopter terms into ETHOS core.
- Do not make hosted CI, assistant memory, MCP, ACP, or Backlog/intake a truth
  store.
- Do not require every daily command to run full tests, build, and deep
  OpenSpec validation.

## Decisions

1. **Trust state is explicit, not inferred from successful planning.**
   Dry-run proof returns `ready` when static admission and graph planning pass.
   It returns `gapped` on admission failures. It never returns `proven` because
   no required gate has executed. This preserves fast daily checks while ending
   the current false-positive proof state.

2. **Claim trust review extends the existing claim digest checker.**
   The current `claims_report()` already has the right home and evidence digest
   discipline. The productized model adds optional-but-enforced fields for
   active claims: `boundary.owner`, `boundary.scope`, `carriers.openspec`,
   `promotion.targets`, `evidence.commands`, `fallback`, and `kill_signal`.
   Existing legacy claims can be migrated in this batch rather than supported
   by a parallel compatibility model.

3. **OpenSpec lifecycle review composes official CLI output with ETHOS
   admission.** The adapter still runs `doctor`, `list`, `status`, and
   `validate --all --strict`. ETHOS then checks repository-specific lifecycle
   facts: active changes must have proposal, design, tasks, delta specs, and a
   bound active claim; archive readiness requires executed proof and promotion
   evidence.

4. **Promotion targets are provider-neutral.** A promotion target is one of:
   source path, test path, schema path, docs path, canonical OpenSpec spec, or
   dated evidence path. A target can be checked for existence and referenced by
   proof without depending on GitLab, assistant tools, or adopter-specific
   providers.

5. **Work Lane and intake are boundary evidence.** Work Lane start/prewrite/land
   report ownership and write admission. Intake reports human/projected state.
   Neither is sufficient for trust without claim, OpenSpec, executed proof, and
   promotion evidence.

6. **reference adopter remains profile-bound.** ETHOS validates parity against reference adopter
   through profile mappings and shadow evidence. Product packages speak in
   subjects, contracts, gates, evidence, promotion, and providers; adopter terms
   stay in profiles or evidence.

## Risks / Trade-offs

- Tightening dry-run proof can break callers that treated `ethos prove --json`
  as a success gate. Mitigation: keep `ok=true` for readiness when static
  checks pass, but report `state=ready` and `executed=false`.
- Requiring enriched claim fields can make existing claim records fail.
  Mitigation: migrate all active ETHOS claim TOML files in this batch.
- OpenSpec lifecycle review can become a second parser. Mitigation: official
  CLI validation remains first; ETHOS only checks product lifecycle carriers
  and promotion evidence.
- Full proof is slower. Mitigation: daily proof stays shape/readiness; release,
  archive, and promotion paths require `--full --execute`.

## Migration Plan

1. Add RED tests for dry-run proof state, executed proof state, claim envelope
   gaps, OpenSpec lifecycle gaps, and adopter parity/profile boundaries.
2. Add provider-neutral schema/contract helpers for trust envelopes and
   promotion targets.
3. Extend claim reporting and migrate active claim files.
4. Extend OpenSpec adapter/reporting with lifecycle review.
5. Tighten CLI proof state transitions and evidence envelope output.
6. Extend Work Lane/intake projection tests where trust-bearing claims require
   carrier binding.
7. Update docs, OpenSpec canonical specs, and evidence.
8. Run full executed proof and OpenSpec validation.

Rollback is a normal branch rollback before closeout. After promotion, rollback
requires reverting schema, CLI, claim, docs, and OpenSpec spec changes together
because proof semantics and claim admission are intentionally coupled.
