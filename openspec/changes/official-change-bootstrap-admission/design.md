## Context

ETHOS correctly makes official OpenSpec the sole tracked intent carrier and a
transient Commitment the acceptance compilation. The current resolver, however,
requires that compilation before admitting writes to the artifacts from which it
is compiled. The former `lane start-change` implementation avoided this circle
by owning a second authoring transaction, but that command and its extra scope,
lineage, receipt, and recovery semantics were correctly deleted. The remaining
model needs a narrow bootstrap state, not restoration of the old mechanism.

## Goals / Non-Goals

**Goals:**

- Permit one official Change to bootstrap itself inside an already-authorized
  Work Lane.
- Derive the admitted paths from official status metadata rather than authored
  scope or path globs.
- Make the bootstrap state transient and replaced automatically by ordinary
  Commitment attribution.
- Return one exact official artifact command as remediation.

**Non-Goals:**

- No ETHOS `start-change` command, tracked Commitment, scope carrier, relation
  record, workflow database, registry, compatibility shim, or negative exception
  list.
- No product-path writes before Commitment compilation.
- No changes to Lease coordinates, lane reconciliation, archive, publication,
  runtime, or remote effects in this atom.

## Decisions

### Reuse current resolution

Extend the existing current OpenSpec resolution to distinguish an official
single-Change artifact graph that is incomplete from invalid or ambiguous intent.
Project its exact Change root and official output paths through the existing
`CurrentScope.material_scope` report. The report is a transient resolution value;
it is neither persisted nor an authorization source independent of the Work Lane
Lease and official OpenSpec observation.

### Admit only the exact official root

The bootstrap owner accepts only repository-relative paths beneath
`openspec/changes/<selected-id>/` that correspond to official artifact outputs:
metadata plus proposal, specs, design, and tasks. It does not use repository
material patterns as bootstrap scope and never admits product paths. Identifier
validation and single active-Change selection remain fail-closed.

### Replace bootstrap after compilation

As soon as `load_openspec_commitment` succeeds, the resolver emits ordinary
Commitment-backed attribution. There is no marker to clear and no historical
bootstrap state to migrate.

### Preserve official authoring ownership

ETHOS reports official `openspec instructions <artifact> --change <id> --json`
or `openspec new change <id> --json` commands. It does not generate artifact
content or restore the deleted Change-authoring state machine. The stale
`lane start-change` requirement is removed from the command-plane spec.

## Risks / Trade-offs

- **Risk: incomplete Change becomes broad permission** — bootstrap scope is the
  exact official Change root and artifact outputs; product paths remain blocked.
- **Risk: two incomplete Changes compete** — retain existing ambiguous selection
  failure; no bootstrap is emitted.
- **Risk: unofficial files under the Change root** — admit only the known official
  metadata and artifact output patterns, not arbitrary README or sidecar files.
- **Trade-off: official creation still needs one initial filesystem effect** —
  `openspec new change` remains the native owner; ETHOS prewrite governs the
  resulting tracked file and all subsequent authoring without another command.

## Migration Plan

1. Preserve the real empty-lane bootstrap failure as a regression.
2. Add unit cases for exact official artifact admission and product/unrelated
   path rejection.
3. Extend current resolution with transient bootstrap scope and official next
   action.
4. Delete stale `lane start-change` command-plane requirements and fixtures.
5. Run focused, affected, architecture, and exact-HEAD proof; archive through the
   official transition, promote by exact CAS, install/read back the accepted
   immutable runtime, and retire the Work Lane.
