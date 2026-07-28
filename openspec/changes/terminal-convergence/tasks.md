## 0. Bind The Terminal Change

- [x] 0.1 Bind this active self-profile change to the terminal product design and owned Work Lane.
- [ ] 0.2 Add failing tests for two-root persistence, open Attestation predicates,
  transient Facts/TransitionPlan, contextual authority/currentness, model gaps,
  byte-stable lease bindings, and history non-authority.
- [ ] 0.3 Map every active carrier and legacy surface to one of: `absorbed`,
  `historical`, or `deleted-after-proof`; block deletion while a semantic delta
  or consumer remains unmapped.

## 1. Cut The Common Generative Kernel

- [ ] 1.1 Remove Commitment process fields, amendment APIs, effective-intent
  folds, closed Attestation kind algebra, and all schemas/tests/readers that
  preserve them.
- [ ] 1.2 Make Attestation predicate/statement/bindings/validity/verifier the
  open immutable envelope; unknown predicates remain non-authorizing.
- [ ] 1.3 Rename all transition inputs and digests to `commitment`; delete
  `contract` aliases and dual carriers. Keep Facts and TransitionPlan
  transient and regenerate their schemas from the single model owner.
- [ ] 1.4 Unify verdicts as `pass | block | unknown`; unknown required inputs
  block effects and no quality warning can coexist with pass.

## 2. Replace Parallel Truth With Contextual Resolution

- [ ] 2.1 Implement five-role carrier extraction and transient descriptor
  diagnostics; reject unknown role semantics as `model_gap`.
- [ ] 2.2 Replace global rank/currentness indexes with the local
  subject/predicate/scope/plane/validity resolver and contradiction blocking.
- [ ] 2.3 Remove historical workflow re-evaluation from admission. Validate
  attestation closure over exact commitment, facts, policy, plan, effect, and
  artifact bindings instead.
- [ ] 2.4 Complete exact carrier-byte/tree lease bootstrap and CAS cutover;
  delete all legacy evaluator, repair, dual-read, and fallback paths.

## 3. Make One Transaction Mechanism

- [ ] 3.1 Reduce generic runtime to observe → extract → resolve → compile →
  evaluate → CAS apply → post-observe → attest → project.
- [ ] 3.2 Move fixed command phases, campaign state, task/progress state,
  decision ledgers, claim/chronicle/proof-record planes, and lifecycle read
  models out of generic runtime; delete their current readers and schemas.
- [ ] 3.3 Keep Git effects idempotent and exact-CAS; produce Attestations for
  judgments/effects and use only explicit replay analysis outside admission.

## 4. Separate Product Profiles From Coordination

- [ ] 4.1 Move OpenSpec discovery, validation, archive, and material paths into
  the ETHOS self-profile adapter; prove generic adopt/plan/prove/land works with
  no `openspec/` directory.
- [ ] 4.2 Reduce Worktree Family, lane, lease, handoff, inbox, records, and
  candidate train to scoped resource facts/projections plus attested effects.
  Remove one-Commitment/one-Family, fixed worker/competition limits, and
  transcript dependence.
- [ ] 4.3 Implement capacity/risk/conflict-based collaboration and competition,
  short candidate CAS, vendor-neutral handoff/takeover, orphan unknown state,
  and lossless reconstruction from Commitment, Facts, Attestations, and Git.

## 5. Absorb The Repository Knowledge System

- [ ] 5.1 Rebuild canonical docs, flat DRs, rules, skills, OpenSpec, schemas,
  CI/forge files, evidence, records, and indexes around their selected native
  owners and derived projections; delete duplicate governance prose and manual
  registries.
- [ ] 5.2 Add contradiction/model-gap promotion and retirable-carrier checks to
  the earliest applicable admission path; prove they cover code, tests, docs,
  rules, skills, schemas, CI, and records.
- [ ] 5.3 Normalize physical names and module boundaries by actual semantics;
  split, rename, absorb, or delete ambiguous catch-alls across source, tests,
  tools, configuration, and documentation without compatibility facades.

## 6. Complete Quality And Product Proof

- [ ] 6.1 Declare one admitted owner for each formatting, lint, type, test,
  structural, documentation, schema, dependency, SBOM, provenance, version,
  and release property; route local and hosted checks through it.
- [ ] 6.2 Eliminate warnings and production formatter/lint/type suppressions;
  enforce drift checks, exact source budgets, and quality across every owned
  repository surface.
- [ ] 6.3 Prove Python, Node/polyglot, and docs/infra adopters with no forced
  layout, language, OpenSpec, or provider; prove offline install, profile
  isolation, uninstall cleanliness, and portable CLI/SDK/subprocess contracts.
- [ ] 6.4 Admit MCP or other ecosystem adapters only after conformance proof
  shows one concrete consumer and zero repository truth ownership.

## 7. Close The Campaign Once

- [ ] 7.1 Run format, lint, type, unit, property, model, mutation, integration,
  adopter, package, source-budget, security, SBOM, provenance, and release proof
  at one immutable local HEAD.
- [ ] 7.2 Advance local candidate/dev and protected dev through native audited
  closeout; absorb or retire all owned lanes and verify required immutable
  record packages.
- [ ] 7.3 Publish exactly one `proposal/terminal-convergence`, then independently
  verify GitLab and GitHub CI/CD, protected dev/main, tag, and artifact
  attestations before archiving this OpenSpec change.
