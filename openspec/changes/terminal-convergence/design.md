## Context

The accepted repository has a five-command public loop but also retains a
quality_summary, a separate orient reader, parallel command/schema ownership, custom
graph and source-measurement runtimes, external ownerless-closeout coupling,
large JSON projections, extensive suppression regions, and a package/test
surface far above the declared terminal limits. Multiple historical campaigns
optimized local slices without one terminal campaign controlling preservation,
deletion, cutover, adopter proof, and final closeout.

The canonical architecture and full concern matrix are owned by
`docs/plans/terminal-governance-product-design.md`. This OpenSpec change is the
only active implementation carrier for that design.

## Goals / Non-Goals

**Goals:**

- Reach the canonical product shape through the shortest destructive path.
- Preserve every required capability through scenarios and conformance, not
  compatibility code.
- Make all hard verdicts truthful, compact, current-HEAD-bound, and non-gameable.
- Delete more product, test, tool, document, schema, and config surface than the
  replacement introduces.
- Complete local proof before one final GitLab and GitHub publication closeout.

**Non-Goals:**

- Preserve old Python imports, commands, schemas, branch vocabulary, or wire
  shapes unless the terminal protocol itself requires them.
- Turn ETHOS into an agent runtime, event bus, DI framework, workflow service,
  policy server, or graph database.
- Modify, land, retire, or clean a foreign Work Lane without native authority.
- Implement optional ecosystem services before kernel and adopter conformance.

## Decisions

1. **One campaign and one design owner.** This change and the canonical terminal
   design replace parallel roadmaps, research notes, and progress documents.
   Alternatives that split the work into compatibility phases were rejected
   because they preserve duplicate owners and repeat remote closeout.
2. **Two persistent entities.** `ChangeContract` owns intent and
   `Attestation` owns evidence-bearing statements. RepositoryFacts and PlanIR
   are derived. Separate claim, evidence, decision, event, inbox, experiment,
   handoff, and chronicle databases were rejected as ontology inflation.
3. **Open facts, closed transitions.** Adapters may observe arbitrary facts,
   while PlanIR admits only `Check`, `Decision`, and `Effect` nodes with
   `pass | block | unknown`. This keeps extension flexible without making
   mutation semantics unbounded.
4. **Deletion-first cutover.** False-green verdicts and oversized outputs are
   fixed first; then private source-budget, workstation-control-plane coupling,
   custom graph, command registry,
   empty template, compatibility, and coverage-only surfaces are deleted before
   broader ecosystem work.
5. **Direct mature mechanisms.** Use Pydantic v2 for persisted contracts,
   Cyclopts for CLI, stdlib graphlib for DAG ordering, official CEL for guards,
   Ruff/Pyright/rumdl/dprint/shfmt/ShellCheck/ast-grep/import-linter for quality,
   Hypothesis and Quint for transition properties, and standard supply-chain
   formats. Wrappers around those owners are not admitted without distinct
   semantics.
6. **Family-level collaboration.** One contract derives one Worktree Family.
   Cooperative slots declare disjoint scopes; no more than two competitive
   variants share acceptance and produce a selection attestation. Only one
   canonical head reaches the candidate train.
7. **Adaptive flow control.** WIP is computed from conflicts, resources, proof
   latency, queue age, train throughput, and recoverability. A fixed global
   limit was rejected because it underuses safe independent capacity and does
   not constrain high-conflict work enough.
8. **Three authority planes.** Local use is offline-capable; GitLab and GitHub
   are independent full CI/CD and release planes. One provider never vouches
   for another. `proposal/*` is the sole remote review role.
9. **Terminal budget over local ratchets.** Intermediate growth is allowed.
   Terminal ELOC, output, warning, suppression, coverage, mutation, and semantic
   ownership constraints are hard and cannot be converted into advisories or
   scores.
10. **Ecosystem last.** Language-neutral schemas, TCK, data/subprocess packs,
    MCP/A2A adapters, and optional Copier/Jinja scaffolds ship only after the
    kernel passes three adopter profiles.
11. **Semantic and physical isomorphism.** Every module has one narrow concept,
    one authority owner, and one primary change reason. Ambiguous module names
    require a closed machine role contract; otherwise the module is absorbed,
    precisely renamed, split by real semantic axes, or deleted. ELOC-only splits,
    compatibility facades, and duplicate command ownership are rejected. The
    invariant spans source, tests, tools, and agent scripts, but carrier-native
    syntax is preserved and no file-count metric can mint architecture.
12. **Open-world signals.** Verdicts are closed, but gap and feedback vocabularies
    are open. Taxonomies are rebuildable explanations over observed signals and
    must not reject novelty or force new evidence into an incumbent category.

## Risks / Trade-offs

- **Large breaking cutover** -> keep every step locally provable and commit
  recovery anchors, but delete the superseded owner in the same semantic cutover.
- **Capability loss hidden by ELOC reduction** -> bind every concern to a delta
  scenario, preservation matrix row, mutation/property test, or adopter proof.
- **Foreign lane overlap** -> observe and compare only; absorb solely through
  native handoff/resolution and never mutate foreign paths.
- **Source measurement becomes too weak** -> keep canonical formatting plus
  scc and Python AST/tokenize cross-checks, platform fixtures, and fail-closed
  disagreement without a private worker protocol.
- **Official CEL parity differs** -> run a bounded corpus bake-off, choose one
  engine, and remove the loser in the cutover commit.
- **Provider or network outage** -> finish all local work first; final provider
  attestations remain unknown rather than blocking local verification claims.
- **Campaign duration creates drift** -> refresh the lane base and re-run the
  relevant local proof after accepted changes, while avoiding intermediate
  provider closeout.

## Migration Plan

1. Restore verdict and output truth and bind this campaign to current facts.
2. Delete the largest self-defeating and provider-coupled surfaces.
3. Cut over the semantic kernel and delete old packages/models/schemas.
4. Cut over lifecycle, Worktree Family, candidate CAS, handoff, and branch roles.
5. Cut over quality, warnings, suppressions, SBOM, provenance, and versioning.
6. Prove Python, Node/polyglot, and docs/infra adopter homomorphism offline.
7. Add only the minimal language-neutral protocol, TCK, packs, MCP/A2A, and
   optional scaffold surface.
8. Run complete local proof, create one proposal branch at the immutable terminal
   commit, verify both providers independently, advance `dev`, release `main`,
   verify records, and retire campaign families.

Rollback is Git reversion to the last locally proven recovery anchor. There is
no runtime compatibility mode and no dual implementation rollback path.

## Open Questions

None. New design questions discovered during implementation must first prove
that the existing two-entity model, PlanIR, profile, or pack protocol cannot
express the requirement; otherwise they are implementation details, not new
semantic surfaces.
