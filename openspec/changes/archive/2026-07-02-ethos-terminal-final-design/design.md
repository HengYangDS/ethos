## Context

OpenSpec is ETHOS mandatory governance for specification records and case
carriers. The official OpenSpec CLI owns workspace discovery, status, archive,
and strict spec validation. ETHOS owns product duties around Work Lane admission,
proposal routing, claim binding, evidence sufficiency, archive closeout, and
adopter scaffolding.

`alternate mechanism corpus` contributes useful mechanism patterns: capability registries,
dynamic facets, direct routing, and explicit official-vs-local authority.
`reference adopter workspace` contributes useful repository governance patterns: Agent
Invocation Envelope admission, Claim Kernel projection boundaries, topic-scoped
closeout evidence, and worktree-first coordination. ETHOS absorbs those as
product mechanisms while preserving its own kernel chain:

```text
Authority -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle
```

Claim binds evidence and carriers; Change owns lifecycle. OpenSpec remains a
case/specification carrier, not a second lifecycle owner.

## Design

The final OpenSpec product substrate has four layers:

1. **Official OpenSpec layer**: `config.yaml`, accepted specs, active changes,
   archive command, `doctor`, `status`, and `validate --strict`.
2. **ETHOS routing layer**: `families.toml`, `capability.toml`, decision axes,
   recommended facets, direct live capability names, and proposal metadata.
3. **ETHOS trust layer**: active claims, Work Lane claim binding, promotion
   targets, evidence refs, fallback, kill signal, and archive closeout reports.
4. **Adopter scaffold layer**: READMEs and templates that create an inspectable
   workspace instead of an empty `openspec/` directory.

Agent Invocation Envelope semantics are documented as the product boundary for
mutation authority. A future host or MCP adapter may package the envelope, but
normal mutation authority must still derive from explicit owner, target root,
editor root, write paths, evidence class, and promotion route. Host readiness is
optional host evidence; it does not satisfy repository proof.

Evidence closeout should be topic-scoped in the terminal layout so long-running
proof does not turn into unstructured transcript truth. The terminal target root
is `evidence/`, while the current transitional repository may still carry dated
summaries under `docs/evidence/` until the evidence-root migration lands.

## Alternatives

- Reusing archived OpenSpec productization changes would hide new semantics in
  historical records, so this lane creates a new active change.
- Copying `alternate mechanism corpus` registries directly would import non-ETHOS vocabulary, so
  ETHOS keeps a smaller family/facet contract tailored to repository governance.
- Adopting reference-adopter Claim Kernel ownership literally would conflict with ETHOS'
  product design contract where Change owns lifecycle and Claim binds evidence;
  ETHOS instead absorbs explicit projection and evidence-boundary mechanics.

## Proof Strategy

Proof is staged:

- Official OpenSpec strict validation for active deltas.
- ETHOS lifecycle validation for proposal metadata, capability profiles, and
  claim binding.
- JSON Schema validation for capability profile contracts and live profiles.
- Focused pytest coverage for substrate files and OpenSpec lifecycle behavior.
- `ethos prove --json` readiness before closeout.
