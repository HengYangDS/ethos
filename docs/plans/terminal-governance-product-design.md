---
subject: ethos:terminal-governance-product-design
role: plan
state: canonical
relations:
  canonical_for: terminal architecture and convergence route
  projects: ../governance/product-design-contract.md#model-promotion
---

# Terminal Governance Product Design

Status: canonical terminal plan.

Purpose: project the product contract into the shortest convergence order for
implementation, proof, deletion, adoption, and publication.

See also: [Product Design Contract](../governance/product-design-contract.md) and
[Decision Records](../decisions/README.md).

## Role

This plan owns terminal architecture and convergence order. The [Product Design
Contract](../governance/product-design-contract.md#semantic-kernel) remains the
sole owner of product meaning; this document specifies how implementations,
projections, and deletions converge on it.

## Architecture

### Semantic Authority And Projection Homomorphism

The implementation compiles the semantic kernel into transport and presentation
surfaces without changing assertion identity. Every projection preserves source
identity, provenance, bindings, validity, and an external observation's absence
reason; it cannot mint authority or hide a required gap. Isomorphism is checked
across the product repository and adopters by comparing the same kernel inputs,
verdict boundary, and attestation shape rather than their physical layouts.

### Model Promotion

[Model Promotion](../governance/product-design-contract.md#model-promotion) is
the only response to a lossless-model failure. Its implementation boundary must
preserve the conflicting evidence, block effect and retirement, recompile
affected projections, and prove the replacement has one semantic owner.

### Git-Native Transaction Boundary

Effects bind an exact Git head and declared scope into `TransitionPlan`,
recheck the binding, execute one compare-and-swap, then post-observe and attest.
Worktrees, lanes, leases, and integration refs are resource coordination, not
semantic roots. Their transition may not substitute stale facts, a dashboard,
or a hosted result for the local Git binding.

### Adopter Isomorphism And First-Hour UX

The product repository and adopters run the same kernel through profiles and
adapters, not product cloning. The first hour is deliberately small:

```text
status -> plan -> prove -> land -> publish
```

`status` is the read-only entrypoint. `adopt` proposes an explicit binding to
that loop; an absent optional carrier remains an observed profile fact.

### Product Surfaces And Experience

One typed application service projects the same kernel result to CLI, Python SDK,
schemas/conformance fixtures, optional stateless MCP or A2A adapters, and native
CI/forge carriers. A surface may adapt transport and presentation only; it cannot
recompile policy, retain lifecycle state, or invent a second error taxonomy.

The CLI defaults to concise human output and progressively reveals evidence;
`--json` is stable automation output, not a separate behavior. Diagnostics carry
one verdict, stable code, plain-language cause, exact evidence boundary, singular
next action, and user-decision flag. Adoption is plan-first and idempotent. The
installed product and contributor workflow both execute from an explicit
project-local environment and lock. Recovery starts from Git, OpenSpec, fresh
Facts, and Attestations rather than a surviving chat or proprietary agent state.

The terminal acceptance is task-based rather than screenshot-based: a new human,
an autonomous agent, and an SDK client can each inspect, adopt, prove, recover,
and uninstall a Python, polyglot, or docs/infra repository without learning ETHOS
internals, cloning this repository's layout, parsing prose, selecting among
equivalent commands, or contacting a forge for local validation.

### Feedback Intent Preservation

Convergence maps each accepted feedback item to an invariant, semantic owner,
acceptance, and proof—or records its explicit absence reason. Deletion is
preferred when that mapping shows a carrier duplicates another owner. No
historical wording is preserved merely to satisfy a text-shaped test.

### Campaign Projection And Convergence Route

The terminal Campaign is carried by the sole active `terminal-convergence`
OpenSpec Change and its `tasks.md`. The dependency graph below orders atomic
phase outcomes and their evidence without creating successor Changes, another
task store, or a speculative forest of lanes.

| Phase outcome | Depends on | Independent acceptance |
| --- | --- | --- |
| `accepted-spec-reconciliation` | terminal slice accepted | Stable specs describe implemented behavior and no archived carrier remains current authority. |
| `portable-reference-boundary` | `accepted-spec-reconciliation` | Product references and variable values have positive native owners across every product surface. |
| `transition-invariant-proof` | `accepted-spec-reconciliation` | Reducers and Git/Lease effects have bounded property, mutation, and model evidence. |
| `openspec-18-cutover` | `accepted-spec-reconciliation` | One exact OpenSpec 1.8 executable owns complete-adopter lifecycle semantics; no older reader or prediction path remains. |
| `coordination-reconstruction` | `accepted-spec-reconciliation` | Lane, Lease, handoff, takeover, inbox, family, and record behavior reconstructs from Git, Facts, Commitment, and Attestations. |
| `integration-throughput-housekeeping` | `coordination-reconstruction` | Adaptive admission and short candidate CAS preserve throughput; every authorized residue has one absorption or retirement result. |
| `repository-knowledge-grammar` | `accepted-spec-reconciliation`, `portable-reference-boundary` | Docs, flat DRs, rules, schemas, skills, and specs have narrow owners, strong grammar, and no ambiguous catch-all. |
| `knowledge-evolution` | `repository-knowledge-grammar` | Novelty, contradiction, overlap, learning, absorption, and retirement change the earliest enforceable owner. |
| `hermetic-quality-toolchain` | `accepted-spec-reconciliation` | Project `.venv`, uv, Nox, Hatchling, native formatters, and zero-warning checks are the sole local/hosted execution owners. |
| `forge-projection-homomorphism` | `repository-knowledge-grammar`, `hermetic-quality-toolchain` | GitLab and GitHub are independent complete projections of one portable contract. |
| `terminal-compression` | `portable-reference-boundary`, `repository-knowledge-grammar`, `hermetic-quality-toolchain` | Repository-wide architecture, duplication, coverage, and ELOC constraints pass with no suppressions or compatibility residue. |
| `adopter-product-surfaces` | `openspec-18-cutover`, `coordination-reconstruction`, `hermetic-quality-toolchain` | Three adopter shapes and CLI, SDK, JSON, schema, MCP/A2A projections prove the same kernel and first-hour UX. |
| `workflow-method-evaluation` | `adopter-product-surfaces`, `hermetic-quality-toolchain` | Matched evaluation admits only methods or tools that improve completion, time, token, recovery, and terminal size without a second owner. |
| `terminal-local-closeout` | all preceding local outcomes | One immutable HEAD passes full local proof, advances candidate and `dev`, and retires every owned lane. |
| `dual-provider-publication` | `terminal-local-closeout` | One `proposal/*` sequence proves and publishes the same signed artifacts independently on GitLab and GitHub. |

Each row remains an independently provable phase outcome in the current Change.
Rows may collaborate concurrently only when their dependency and scope facts
admit it; completion remains owned solely by the corresponding tasks.

## Convergence Rules

1. **Promote before compatibility.** Replace a missing model boundary before
   introducing an alias, fallback, or shim; delete the residue in the same
   bounded change when proof permits.
2. **Compile, do not narrate.** Keep authority, bindings, invalid states, and
   effects in the owning contract and executable verifier; documentation links
   to them as a projection.
3. **Separate planes.** Local proof, GitLab observation, and GitHub observation
   produce distinct attestations and cannot imply one another.
4. **Retire only after relation proof.** A carrier is removed only after its
   inbound consumers, preserved history, replacement owner, and projection
   references are checked.
5. **Prove across shapes.** Product, code, and documentation adopters demonstrate
   the same input-to-verdict relation while retaining their native carriers.
6. **One obvious safe path.** Defaults select the least-powerful useful operation;
   advanced controls appear only when current facts require the distinction.
7. **Errors are continuations.** Every non-pass result preserves the diagnostic
   code and evidence boundary and identifies exactly one safe next action or one
   explicit user decision.
8. **Surfaces stay projections.** CLI, SDK, MCP/A2A, CI, forge, and generated
   scaffolds share contracts and conformance tests; none owns duplicate policy or
   durable progress.
9. **Close semantic increments.** Each phase produces an independently
   reviewable and provable terminal-state delta. Carrier topology follows intent
   cohesion and progress ownership rather than imposing one Change per outcome.

## Completion Boundary

Terminal convergence is verified only when the kernel, Git-native effect
boundary, open invalid-state handling, profile isomorphism, and projection
relations pass their owners' checks. A passing local architecture test is not a
claim of hosted publication, adoption completion, or historical archive repair.
