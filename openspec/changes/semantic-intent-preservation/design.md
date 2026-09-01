## Context

See [proposal.md](proposal.md) for motivation. The bounded recovery source was
assembled from ETHOS-related Codex and Claude records dated from 2026-07-01
through 2026-09-01. It contains 5,116 deduplicated records from 131 sessions:
4,144 direct inputs, 809 delegated reports, 106 inherited goal statements, 44
response-only recoveries, and 13 attachment requests. Session metadata confirms
that the current task was forked from `[ETHOS] 拒绝手撸`; the large AIGW/Proxy
task is an adopter evidence source, not the predecessor product authority.

The candidate corpus deliberately over-collects from ETHOS-associated sessions.
It therefore contains product guidance, adopter observations, one-shot
operational instructions, repeated continuations, tool incidents, attachment
requests, and a small amount of unrelated inherited context. A source record is
not a product requirement merely because it appears in the corpus.

The primary extract has SHA-256
`19aef5fee52f9009c9f758a771ff81256efca4059abeb4fc697270adf3d633be`.
The complete temporary input set is:

| Input | SHA-256 |
| --- | --- |
| `/private/tmp/ethos-source-records-frozen-20260901.jsonl` | `19aef5fee52f9009c9f758a771ff81256efca4059abeb4fc697270adf3d633be` |
| `/private/tmp/ethos-source-domain-map-20260901.jsonl` | `e6d7d16ab05ead162e38df6fb2537de3cd034083fdc1a8ae30aa5e69d13fa742` |
| `/private/tmp/ethos-source-domain-summary-20260901.json` | `9e85848a7ed1b2b5b936776294374baff2b9ba3b5bb69cba75d64df914d5448a` |
| `/private/tmp/ethos-semantic-adjudication-20260901.md` | `401ff019ef32435e5e0985e83c3605e45b255666209771a3c3eb30a2202bd481` |
| `/private/tmp/classify_ethos_semantics.py` | `d25486790b64603e0ea89005a93fd5d2657a0cb60d8fa58584976470fea4950e` |
| `/private/tmp/ethos_semantic_panorama.py` | `882da46ea1fe352a137fb743d8522cfa910bad27096a29ddfc5df43351a81a16` |
| `/private/tmp/ethos-semantic-panorama-current.json` | `c9edfe10210f9ac60ebf8856d9220239145cfc4025339227508775a13033bba7` |
| `/private/tmp/ethos-semantic-panorama.tsv` | `95df4590d5783950a2fab1d02fea7c3b787afc7a831d39bb4c110bdadfbdba05` |

These files are bounded recovery inputs, not durable product identifiers or
current authority. The classifier is a retrieval aid only: keyword matches and
fallback labels cannot accept, reject, or supersede meaning.

## Goals / Non-Goals

**Goals:**

- preserve every distinct, still-valid product obligation from the bounded
  source;
- make supersession, rejection, and uncertainty explicit rather than silently
  dropping them;
- place accepted meaning in an existing unique owner;
- leave one finite implementation route and delete the temporary recovery
  machinery.

**Non-Goals:**

- retaining raw conversations or every repeated wording in Git;
- creating a feedback ledger, requirement registry, second roadmap, workflow
  database, or permanent source-to-requirement map;
- treating adopter-proposed remedies or historical implementation as design
  authority;
- implementing the recovered product gaps in this Change.

## Decisions

### Recover semantic obligations, not message count

Completeness is semantic: repeated wording maps many-to-one to a single
obligation, while one message may yield several obligations. The recovery must
cover the declared source boundary and all distinct meanings; equal source and
requirement counts would instead preserve noise and create a new ontology.

Alternative rejected: commit the 5,116 records or a generated registry. That
would expose private operational context, make obsolete wording active, and
create a second authority that must forever be synchronized.

### Adjudicate source classes before accepting a design

The order is:

1. identify direct guidance and explicit later supersession on the same subject;
2. split delegated material into observation, inference, and remedy;
3. compare observations with fresh repository/runtime facts;
4. classify each distinct obligation as accepted, superseded, pending
   verification, or rejected;
5. map accepted meaning to one existing owner and name its acceptance and proof;
6. keep non-accepted rationale in this official Change, then archive it.

Agent summaries, memory, tests, and current code are evidence about state. None
may reverse-define user intent merely because it already exists.

Records that do not express an ETHOS product obligation are closed without
inventing one. This includes acknowledgements and continuation prompts,
temporary execution or presentation instructions, duplicate wording, test
payloads, unavailable attachment-only requests, other-project operations, and
host or provider incidents whose owning boundary is outside ETHOS. When such an
incident exposes a reusable ETHOS boundary defect, only that generalized defect
is admitted; credentials, private paths, and adopter-specific remedies are not.

### Use existing carriers by semantic lifetime

| Meaning | Unique carrier | Lifetime |
| --- | --- | --- |
| Current product meaning and invariants | `docs/governance/product-design-contract.md` | canonical until explicitly superseded |
| Remaining dependency order, exit conditions, and proof boundaries | `docs/plans/terminal-governance-product-design.md` | canonical while convergence remains open |
| One bounded semantic recovery or product change | official OpenSpec `proposal/specs/design/tasks` | active, then immutable archive/history |
| Irreducible rationale spanning multiple Changes | `docs/decisions/<semantic-name>.md` | only while alternatives, consequences, and revisit condition remain useful |
| Executable admission or behavior | source, schema, native configuration, rule, and test owner | current implementation |
| Raw transcripts, extracts, classifiers, scratch matrices | owner-scoped temporary storage | deleted after coverage proof |

A Decision Record is not a feedback receipt. It is admitted only when deleting
it would lose a still-relevant choice among alternatives that neither the
current contract nor source can express clearly.

### Preserve the complete terminal semantic map

The recovered source resolves to the following product domains. The table is a
bounded migration map for this Change, not a new active roadmap.

Every row below is accepted as current product meaning. “Batch” names unfinished
implementation and proof; it is not evidence that the behavior already exists.

| Domain | Accepted terminal meaning | Current owner / implementation batch |
| --- | --- | --- |
| Product kernel | local-first proof-carrying compiler and transaction protocol | Product contract; plan batches 2-5 |
| Entity admission | delete, reuse, merge, simplify, then add only an indispensable unique owner | Product contract invariants; repository audits |
| OpenSpec and Commitment | official OpenSpec is sole tracked intent; Commitment is transient; Attestation is durable | Product contract; plan batch 2 |
| Change relations and learning | DAG queries and hypothesis/experiment remain derived capabilities, not stored graph/DSL state | Product contract; plan batch 2 |
| Change granularity | one coherent reviewable/provable outcome; semantic independence, not file count, decides splitting | Product contract and plan route |
| Facts, result, and resolver | fresh Facts and one deterministic resolver/result/continuation drive all public readers | Product contract; plan batch 2 |
| Lane and Lease | Lease contains only lane, holder, generation, expiry; public reconciliation covers loss and dead owners | Product contract; plan batch 3 |
| Git effects and recovery | exact CAS, post-observation, idempotent resume or bounded compensation, no command-local state machines | Product contract; plan batch 3 |
| Branch and review roles | `work/*` authors, candidate integrates, `proposal/*` reviews, `dev` accepts, `main` releases | Product contract; plan batch 5 |
| Proposal retirement | selected object in `dev` plus closed review ref; independent of later `main` promotion | Product contract; plan batch 5 |
| Local and remote topology | local Git owns objects; zero, one, or many independent peers receive the same OIDs | Product contract; plan batch 5 |
| Proof and assurance | exact predicate/binding selects proof; local, independent, forge, CI, release, and runtime planes remain distinct | Product contract; plan batches 2 and 8 |
| Runtime and version identity | product, distribution, source/tree, package, runtime, selected role, and installed binding are distinct and immutable | Product contract; plan batch 4 |
| Toolchain and diagnostics | repository lock selects execution; errors preserve exact boundary and one non-replaying next action | Product contract; plan batch 4 |
| Adopter isomorphism | same kernel and protocol, native repository layouts, no adopter compatibility carrier | Product contract; plan batch 8 |
| Module layout | physical boundaries follow semantic ownership; no empty shells or suffix-flat pseudo-modules | `rules/module_layout.md`; plan batch 6 |
| Documentation and decisions | one docs entrypoint, quickstart under guides, necessary READMEs only, irreducible semantic decision records only | Product contract and docs registry; plan batch 6 |
| Configuration and quality | one native executable owner per property across every admitted carrier; modern Python within the declared compatibility floor; no copied policy, aggregate-budget compensation, or line-count architecture | Product contract; plan batch 6 |
| Temporary resources and supply | exact owner/liveness, normal finalization, dead-owner scavenging, shared content-addressed supply, resource budgets | Product contract; plan batch 7 |
| Identity, signature, CI, and release | author, signature, transport, forge verification, CI, release, local proof, and runtime are separate evidence planes | Product contract; plan batch 8 |
| Governance recovery | bounded maintainer break-glass keeps products releasable when ETHOS is inconsistent, followed by audited re-entry | Product contract; plan batches 3-5 |
| Product ecosystem and portability | stable standards and mature capabilities are evaluated before custom machinery; the same kernel supports Python, polyglot, docs/infra, macOS, Linux, Windows, local-only, and hosted shapes through native adapters | Product contract; plan batches 4, 6, and 8 |
| Public meaning and visual projection | documentation, architecture views, diagrams, brand assets, and examples preserve source meaning, remain accessible and navigable, and follow `信、达、雅` without becoming another ontology | Product contract, docs registry, and brand/projection owners; plan batch 6 |
| Execution discipline | live-state first, protected foreign work, no unauthorized subagents, no partial completion claims, optional skills and memory remain non-authorizing, and progress optimizes verified semantic throughput | agent rules and plan convergence rules |

### Adjudication closure

The accepted map above subsumes twenty terminal requirement groups in the
temporary adjudication. The following conflicting or obsolete formulations are
not current requirements:

- durable tracked `commitment.toml`, `scope.toml`, rebind/successor carrier
  families, or archive scanning as an active database;
- treating Commitment and Attestation as two persistent semantic roots;
- persisted predecessor/successor fields, a research DSL, or a mutable
  hypothesis/experiment ledger;
- waiting for `main` before retiring a proposal already accepted into `dev`;
- making GitLab, GitHub, any provider, WCP, Workstation, Codex, or another agent
  runtime mandatory to the ETHOS kernel;
- recreating objects, signatures, or history independently per remote;
- using file count, directory width, or one aggregate line budget as
  architecture authority;
- restoring every historical Decision Record or introducing numbered `DR-*`
  identity; and
- creating a feedback ledger, registry, blacklist, compatibility layer, or
  memory-backed current truth to preserve this recovery.

No implementation or hosted-state claim is accepted from the corpus alone.
Open implementation obligations remain pending in the dependency-ordered
terminal plan until their own Changes and proof surfaces close them. This
separates accepted product meaning from unverified implementation state.

### Close the recovery instead of preserving its tooling

This Change is complete only when the product contract and terminal plan express
the accepted map without contradiction, the repository-governance delta
validates, the documentation/rule projections point to those owners, and all
eight temporary recovery inputs listed above can be removed without losing
current meaning or the ability to execute the remaining plan.

## Risks / Trade-offs

- **A compressed invariant may omit a meaningful distinction.** -> Validate
  every domain against direct guidance, delegated observations, current contract,
  current plan, and current repository facts; unresolved distinctions remain
  pending rather than guessed.
- **The official Change could become a permanent alternate model.** -> Keep only
  migration rationale here; current meaning and open work live in the two
  canonical documents, and archive this Change after acceptance.
- **Another Lane edits the same documentation topology.** -> This Change does
  not create `docs/decisions/` or absorb that Lane; later integration must use
  exact semantic comparison and retain only non-duplicated rationale.
- **Deleting temporary inputs too early would destroy auditability.** -> Delete
  only after tracked coverage, validation, commit, and readback prove no current
  dependency on them.

## Migration Plan

1. Update the Product Design Contract with source classes, adjudication states,
   carrier placement, and semantic-completeness criteria.
2. Update the Terminal Governance Product Design with the recovered domain map,
   remaining batch ownership, and source-recovery exit conditions.
3. Update documentation and agent rules to reject temporary or conversational
   authority and route future broad recovery through an official Change.
4. Validate the OpenSpec delta and repository documentation/semantic gates.
5. Prove that the tracked owners are self-contained, delete only the eight named
   temporary recovery inputs, and verify their absence and the absence of any
   tracked dependency on them before final exact-HEAD proof and archive.
