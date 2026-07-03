## Context

The terminal design says the mandatory choke point is the pre-tool hook. Git
hooks and CI are necessary fallback and proof layers, but they run too late to
prevent direct tracked file mutation. Existing ETHOS code already classifies
checkout roles and evaluates `ethos lane prewrite`; the missing product piece
is a hook-facing decision report that hosts can call before write-capable tools
or shell commands run.

The absorbed pattern from `alphasim-dmgr-fix-b3` is the lane discipline around
protected roots, local candidate staging, explicit closeout, and evidence-bound
claims. ETHOS keeps that as `campaign -> OpenSpec change -> Work Lane ->
claim/evidence -> accepted-root closeout -> retire`, not as a single total
lane. The campaign manifest now makes that explicit with `ordinal`,
`depends_on`, and `lane_topology.mode = "strict_serial"`, so downstream steps
can activate only after upstream lane closeout is retired. The absorbed pattern
from `di-effect` is direct capability routing, facet metadata, and
hook/projection checks as declared controls; ETHOS narrows that to its own
command plane and avoids importing di-effect's broader ontology.

## Design

Add `ethos_adapters.hook_admission` as a thin runtime adapter. The adapter is
read-only except for the fact that callers may use its decision to permit or
block a later write. It returns a product JSON shape with:

- hook layer identity and stage duty;
- target root, checkout role, branch, editor root, and target paths;
- prewrite admission payload when the layer can mutate tracked files;
- command risk classification for pre-run hooks;
- post-write fuse gaps for protected-root dirtiness or unexpected tracked
  paths;
- fallback/proof metadata for Git and CI layers.

The CLI adds `ethos hook admit`. This is a maintainer/reference command, not a
new public workflow root. Normal user flow stays `status -> plan -> prove ->
land -> publish`; write-capable hosts use the hook command as a machine
admission endpoint.

## Boundaries

Official OpenSpec owns the change carrier and strict validation. ETHOS owns the
repo-local runtime decision report, Work Lane admission binding, claim/evidence
binding, and campaign lane-topology closeout state.

The hook runtime does not install host hooks in this lane. That would require
provider-specific projection work and belongs in later scaffold/projection
lanes. This lane instead makes the product decision callable and testable so
hosts have one command to invoke.

## Rollback

Remove the hook admission module, CLI command, command registry entry, docs,
claim/evidence, and OpenSpec deltas. `ethos lane prewrite` continues to provide
manual degraded-mode admission, so rollback does not remove the existing Work
Lane safety primitive.

## Proof Strategy

RED tests first cover:

- pre-tool blocked accepted-root mutation before write;
- pre-tool admitted owned Work Lane mutation with matching editor root;
- pre-run mutation-risk commands blocked without admitted target paths;
- post-write fuse on protected-root dirty state;
- CLI JSON contract for `ethos hook admit`.
- changed-scope playbook routing for `evolution/**` campaign manifests and
  source skill activation.

GREEN implementation then wires the adapter and command plane, updates the
campaign manifest, and records claim/evidence. Full closeout proof must include
focused tests, full tests, Ruff, OpenSpec strict validation, lifecycle review,
claims, schemas, report, executed proof, build, land, accepted-root closeout,
and Work Lane retirement.
