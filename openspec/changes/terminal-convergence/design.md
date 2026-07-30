## Context

ETHOS currently overlays a renamed vocabulary on several older systems: global
source ranking, a fixed OpenSpec lifecycle, historical re-evaluation, campaign
and decision ledgers, currentness indexes, and coordination models that mix
intent with resources. These systems overlap docs, rules, skills, schemas, CI,
records, and runtime code. They cannot evolve coherently because each can claim
to be the source of current truth.

The canonical target is the common generative kernel in the Product Design
Contract. This change is the ETHOS self-profile implementation carrier, not a
new product ontology.

## Decisions

1. **Two persistent roots.** Commitment is immutable normative intent;
   Attestation is an immutable verifier-bound statement. Facts and
   TransitionPlan are transient. A changed intent creates a new Commitment;
   no amendment chain survives.
2. **Five processing roles.** Every carrier is native, projection, adapter,
   fact, or history. The resolver may emit transient descriptors, but no
   universal manifest, registry, ledger, or index is persisted.
3. **Contextual authority.** Authority/currentness resolves per subject,
   predicate, scope, plane, validity, and context. Global rank, timestamp-only
   selection, `CURRENT`, accepted/superseded directory status, and manual
   indexes are deleted as authority devices. Ambiguity blocks; valid novelty is
   `model_gap`.
4. **One generic transition mechanism.** Observe, extract, resolve, compile,
   evaluate, exact CAS apply, post-observe, attest, then project. Command
   sequences, archive actions, campaign displays, lane phases, and provider
   pipelines are profile projections; no fixed lifecycle is embedded in the
   kernel.
5. **Effects close through exact bindings.** A TransitionPlan contains exact
   commitment, fact, prior-attestation, policy, and effect bindings. The adapter
   rechecks preconditions at CAS time. Post-observation and an Attestation—not
   a replayed historical workflow—establish what occurred.
6. **Self profile is optional to adopters.** OpenSpec is a native carrier plus
   adapter for ETHOS's self profile. Its official CLI owns validation and
   archival. A generic adopter with no OpenSpec must compile and prove a
   transition from its selected native carrier.
7. **Coordination is derived.** Worktrees, refs, leases, families, inboxes,
   handoffs, candidate queues, records, dashboards, and taxonomies are resource
   facts or projections. They never preserve intent alone. Capacity and
   competition are policy/fact decisions, not fixed cardinalities.
8. **Absorptive evolution.** Every legacy carrier is classified as absorbed,
   historical, or deleted-after-proof. A contradiction/model gap preserves its
   scenarios, promotes the smallest model boundary, recompiles dependents, and
   only then retires residue.
9. **Direct mature capabilities.** Use Pydantic v2 for portable boundary
   contracts, small frozen standard-library values internally, Cyclopts,
   `graphlib.TopologicalSorter`, the selected official CEL engine, native Git
   CAS, and standard supply-chain formats directly. Do not add attrs as a
   parallel model system. Frameworks, generators, Jinja, DI, event buses,
   plugin layers, and workflow runtimes require a concrete consumer,
   conformance evidence, uninstall cleanliness, and net deletion.
10. **One quality owner per property.** Local and hosted execution consume the
    same declarations. Warnings, suppressions, unknown required facts, and
    projection drift fail closed. JSON receives schema validation and canonical
    serialization from its declared owner, not an invented formatter.
11. **Lossless intent closure.** Accepted feedback is reduced into independent
    semantic obligations before planning artifacts are replaced. Within the
    same authority and scope, a later explicit ruling supersedes an earlier one;
    the earlier ruling remains history and cannot silently return as current
    policy. Every obligation maps to an existing semantic owner, requirement,
    stable task, acceptance condition, and verifier, or records an explicit
    rejection or deferral reason. Unmapped meaning and unresolved contradiction
    are `model_gap` and block retirement and campaign closeout. This closure is
    compiled from tracked carriers and current instructions; it is not another
    persistent ledger or task store.
12. **Stable execution identity and evidence.** Task identifiers are never
    reused or renumbered to make a redesign appear incomplete or complete.
    Refinement preserves completed state and its commit or proof evidence,
    explicitly supersedes obsolete tasks, and adds newly discovered work under
    new identifiers. The first incomplete task is the campaign critical path;
    every phase has an observable exit condition, and elapsed activity without
    a terminal-state delta is not progress.

## Alternatives Considered

| Alternative | Decision | Reason |
| --- | --- | --- |
| Rename legacy concepts in place | Rejected | Labels do not remove parallel authority or historical re-evaluation. |
| Make every repository use OpenSpec | Rejected | It confuses ETHOS self governance with the general product boundary. |
| Keep a global authority order | Rejected | Different subjects and planes require simultaneous local authorities. |
| Retain amendment and ledger chains | Rejected | They create mutable semantic roots and an additional currentness system. |
| Add a framework for coordination | Rejected | No proved consumer yet justifies its semantic and maintenance cost. |
| Delete all history | Rejected | Immutable bytes may be needed for recovery and audit, but not as current truth. |
| Replace tasks wholesale after redesign | Rejected | It destroys progress identity, hides dropped obligations, and permits old decisions to reappear. |
| Preserve every conversation sentence as a repository ledger | Rejected | Raw dialogue is context; accepted independent obligations belong in their semantic owners and verifiable tasks. |

## Migration Risks

- **Carrier/model cutover can change digests.** Bind leases and effects to exact
  carrier bytes/tree digests and perform one explicit CAS bootstrap; do not
  retain dual evaluators or dual readers.
- **Deletion can lose unique meaning.** Inventory independent semantic deltas
  before deletion; preserve history where required and prove no active consumer.
- **Optional OpenSpec can regress the self profile.** Keep self-profile adapter
  scenarios while proving a no-OpenSpec adopter path.
- **Parallel work can race.** Use exact scopes, fresh facts, resource leases,
  and short CAS integration; never infer ownership from visibility.
- **Projection drift can conceal inconsistency.** Require declared source
  bindings and generated/diff checks at the earliest feasible gate.
- **Long-running activity can conceal non-convergence.** Keep one ordered
  critical path, require a verified terminal-state delta at every phase exit,
  and move independent review off the mutation path.

## Migration Sequence

1. Restore the pre-cutover kernel-test and carrier-classification tasks under
   their original identifiers, close accepted feedback without resetting stable
   task identity, and finish the current OpenSpec replica-deletion slice.
2. Cut Commitment, Attestation, Facts, TransitionPlan, verdict, and digest
   semantics; delete amendment and closed-kind paths.
3. Replace authority rank/currentness/legacy replay with contextual resolver,
   five-role extraction, model-gap handling, and byte/tree-bound lease cutover.
4. Move fixed lifecycle and OpenSpec-only assumptions into the ETHOS self
   profile; reduce coordination to resource facts plus attested effects.
5. Reclassify and absorb docs, DRs, rules, skills, schemas, CI, records,
   evidence, and OpenSpec material; delete only after semantic proof.
6. Collapse quality/supply-chain tooling, remove warnings/suppressions, prove
   three adopter shapes and portable interfaces, then run one local and one
   dual-provider campaign closeout.
