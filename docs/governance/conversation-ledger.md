---
subject: ethos:conversation-ledger
role: governance-ledger
state: active
relations:
  canonical_for: conversation-derived product gaps
  informs:
    - ethos:self-evolution
    - ethos:product-ontology
    - ethos:adoption
---

# Conversation Ledger

This ledger records product requirements and corrections that came from the
long ETHOS design conversation. It is not a substitute for specs, code, tests,
or release evidence. Its job is narrower: preserve the requirements that were
easy to lose during implementation, make gaps reviewable, and feed the
self-evolution campaign.

## Situation

ETHOS means Evidence-backed Trust for Human-agent Operational Stewardship. The
intended product is a kernel-first governance framework for human-agent
repository operation. It governs intake, contracts, isolated work, evidence,
quality, assistant projections, release, reports, and evolution through one
public command plane.

The current product repository has made alpha progress, but the conversation
established that alpha progress is not the terminal state. Missing or shallow
areas must remain visible until implemented, tested, documented, and proven.

## Fact Boundaries

- ETHOS product behavior belongs in packages named ethos-*.
- Adopter-specific semantics belong in profiles or adopter repositories.
- alphasimdmgr and dmgr contracts are reference-adopter concerns, not core
  product assumptions.
- Superpowers is an external method pack and execution aid, not repository
  truth.
- OpenSpec must be an official-native governance workspace under openspec.
- Repository-local .agents/skills files are thin playbook projections, while
  generated skills must still meet official-quality assistant skills
  expectations.
- Assistant host memory, fast mode, goals, subagents, and doctor output are host
  capability signals. ETHOS should model and verify their use without treating
  host-local state as durable truth.
- backlog-md is an intake-ledger adapter opportunity, not a proof or contract
  source of truth.
- Product behavior must not be moved into tools directories.
- tools/agent in an adopter repository should be classified as adopter legacy,
  reusable adapter candidate, or retired residue through explicit adoption
  rules.
- .mailmap must not be reintroduced in this product repository.
- Package root __init__.py files must not re-export module surfaces.

## Kernel Vocabulary

The internal model should stay smaller than the number of commands:

- Subject: the thing being changed or governed.
- Contract: the invariant or promised behavior.
- Transition: the planned movement from one state to another.
- Inscription: tracked source, docs, schemas, configs, or evidence written.
- Chronicle: durable record of what happened and why.
- Evolve: opportunity, hypothesis, challenge, canonization, or retirement.

The public command plane should remain ETHOS-first. Older public roots from
adopter-era tooling may exist only as historical or internal engine vocabulary,
not normal user workflow vocabulary.

## Requirement Ledger

| ID | Requirement | Current Risk | Required Landing Evidence |
| --- | --- | --- | --- |
| CL-001 | Split governance into bounded packages such as evidence, quality, policy, spec, and evolution; keep governance orchestration thin. | ethos-repository can become a governance junk drawer. | Product ontology, package README, tests proving MECE ownership. |
| CL-002 | Generate or maintain official-quality assistant skills, not minimal hand-written placeholders. | Skills may exist but fail provider expectations. | Skill quality tests, templates, and lifecycle docs. |
| CL-003 | Treat activation.toml as an ETHOS registry, not official skill metadata. | Registry and provider metadata can be conflated. | Schema and docs that separate registry from projection. |
| CL-004 | Keep Superpowers external and observable through method-pack adapters. | Vendoring or silent non-use can break trust. | Adapter docs, report fields, and execution evidence. |
| CL-005 | Model assistant host memory, fast mode, goals, subagents, and doctor as host capability inputs. | Host affordances can be forgotten or treated as truth. | Host capability check and report output. |
| CL-006 | Productize backlog-md as an intake-ledger adapter where appropriate. | Intake may stay adopter-private. | Intake adapter spec, scaffold, and sample validation. |
| CL-007 | Classify adopter tools/agent surfaces explicitly during adoption. | Reusable agent utilities can be lost or incorrectly productized. | Adoption report with retire, project, or profile decisions. |
| CL-008 | Implement official OpenSpec lifecycle including proposal, delta validation, delta-to-canonical sync, archive, and self-audit. | OpenSpec may be present but not deeply governed. | OpenSpec strict validation plus lifecycle tests. |
| CL-009 | Maintain MECE spec families aligned with product package families. | Specs can drift into duplicate or missing capabilities. | Spec family test and product ontology cross-check. |
| CL-010 | Build real self-evolution, including opportunities, hypotheses, exhaustion challenge, closeout, and retirement. | Self-evolution can become a static document. | Evolution ledger state machine and CLI/report tests. |
| CL-011 | Build a real gate runner that plans, executes, records, and explains gates. | Proof can remain a summary wrapper. | Gate schema, action graph execution tests, evidence output. |
| CL-012 | Enforce format, artifact, and evidence governance. | Generated state and durable truth can blur. | Format policy, artifact policy, and location checks. |
| CL-013 | Keep dmgr as a reference adopter, the dmgr reference adopter, with its own profile and evidence. | Core can accidentally hardcode dmgr or alphasim. | Reference adoption fixture and boundary tests. |
| CL-014 | Express dmgr contracts through generic contract-profile mechanisms. | Raw/cache/alphasim rules can become product-private code. | Contract profile schema and adopter proof mapping. |
| CL-015 | Complete release and publish governance, including hosted parity and break-glass semantics. | Local checks can be mistaken for release readiness. | Release policy tests, GitLab checks, provenance evidence. |
| CL-016 | Verify GitLab commit signature status as a release signal. | Local GPG signature can still be Unverified on GitLab. | Hosted signature check in release report. |
| CL-017 | Prevent .mailmap return. | Identity cleanup can reintroduce repo-level rewriting artifacts. | Architecture test asserting no .mailmap. |
| CL-018 | Treat historical commit identity rewrite as an explicit migration plan only. | History rewrite can be attempted casually. | Migration design, authorization, and hosted verification. |
| CL-019 | Redesign docs information architecture for clarity, fidelity, and elegance. | Docs can be complete but hard to navigate. | Docs registry, taxonomy, stable paths, and UX review. |
| CL-020 | Make init scaffolding create the full governance skeleton. | New projects can start with incomplete ETHOS structure. | Scaffold tests covering docs, schemas, OpenSpec, skills, rules, state ignore. |
| CL-021 | Harden npm distribution adapter and registry publication path. | Node wrapper can exist but break in real use. | Package smoke, bin smoke, and publication checklist. |
| CL-022 | Preserve one public command plane. | Legacy public vocabulary can leak back into current docs. | Command registry scan and docs command-example tests. |
| CL-023 | Feed hosted CI parity back into evidence, not a separate truth store. | Hosted checks can diverge from local proof semantics. | CI adapter report and evidence envelope. |
| CL-024 | Make standards adoption executable and lifecycle-managed. | Standards can stay aspirational. | Standards registry, adapters, and exit strategies. |
| CL-025 | Keep conversation-derived requirements auditable. | The agent can forget or narrow scope again. | This ledger linked from docs index and self-audit. |

## Nonclaims

This ledger does not claim that every item above is implemented. It states that
the items are known requirements or gaps. A future closeout can mark them as
implemented only after source changes, tests, docs, and evidence agree.

## Productization Rule

When in doubt, productize the abstract mechanism and keep adopter vocabulary in
profiles. The core should speak in subjects, contracts, transitions,
inscriptions, chronicles, evolution, evidence, gates, policies, projections,
and releases. Adopters then bind those abstractions to dmgr, alphasim,
raw/cache parity, hosted GitLab, or local assistant surfaces.
