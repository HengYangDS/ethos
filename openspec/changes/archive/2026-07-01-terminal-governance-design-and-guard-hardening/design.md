## Context

ETHOS is being redesigned as a repository governance product. The current lane
is a planning and design lane, not the full terminal implementation lane.

Two process failures shaped this change:

1. A tracked write reached the wrong repository root because a mutation tool
   used implicit session context instead of an explicit target root.
1. Design and rules work started before a dedicated OpenSpec change existed.

Both are governance failures. They are not just operator mistakes. A repository
governance product must make the valid path cheaper and earlier than the
invalid path.

## Goals / Non-Goals

**Goals:**

- Record the terminal ETHOS design in tracked docs and OpenSpec artifacts.
- Keep `AGENTS.md` thin; place durable rule semantics under `rules/` and
  reusable procedures under `skills/`.
- Define hook placement for context refresh, pre-tool write admission, pre-run
  command risk classification, post-write fuse behavior, Git fallback hooks,
  and CI/release gates.
- Require non-trivial governance design, rule, skill-system, hook, and product
  shape changes to have an OpenSpec carrier before tracked mutation proceeds.
- Add documentation progressive disclosure so agents do not load the whole
  repository knowledge graph for every task.
- Preserve low-code, declarative, standards-first implementation direction for
  later lanes.

**Non-Goals:**

- Do not implement the final terminal package topology.
- Do not implement the full hook runtime or projection generator.
- Do not change skill manifest schemas or runtime validators in this lane.
- Do not archive existing OpenSpec changes.
- Do not claim terminal design is fully implemented.

## Decisions

### Decision: OpenSpec Is A Pre-Mutation Planning Gate

Non-trivial changes to repository governance semantics must start with an
OpenSpec change or explicitly attach to an active, non-complete change. Existing
complete changes are historical or closure records, not default containers for
new work.

Alternative considered: keep design in docs only. That fails because the
planning carrier, spec delta, tasks, and later archive path become implicit.

### Decision: OpenSpec Is A Product Protocol, Not Just A Folder Gate

Terminal ETHOS treats OpenSpec as the case and specification carrier:
`openspec/specs/` is accepted capability behavior, `openspec/changes/` is
planned delta state, and `openspec/changes/archive/` is historical context.
Each layer has different authority and cannot substitute for the others.

The ETHOS product additions are capability profiles, families, proposal
metadata, direct capability routing, task lifecycle checks, claim/evidence
binding, and closeout guards. These additions stay around the official OpenSpec
model; they do not fork the OpenSpec CLI or create a separate public command
plane.

Alternative considered: only require `openspec validate --all --strict`. That
proves syntax, but it does not prove ETHOS product duties such as Work Lane
attachment, claim binding, archived task state, adopter scaffold completeness,
or whether a live spec edit was in scope for the archived delta.

### Decision: Capability Profiles Carry Routing Ontology

Capability-local `capability.toml` files are the stable routing metadata for
families, owner boundary, primary invariant, routing question, decision axes,
recommended facets, boundary rules, and proof profile. Proposal entries must
name live capabilities directly and record subject, reuse stance, change
stance, and lifecycle/surface/authority facets.

This absorbs the useful `di-effect` practice of capability-local profiles,
family taxonomy, direct routing, reuse metadata, and dynamic facets. ETHOS keeps
the taxonomy smaller and product-neutral: facets help routing and review but do
not create ownership, and no adopter-specific domain terms become product
capabilities.

Alternative considered: keep capability metadata only in narrative docs. That
would make routing, validation, and adopter scaffold generation hand-maintained
and drift-prone.

### Decision: Archive Closeout Adds ETHOS Guards Around Official Archive

ETHOS should call the official archive path, then run repo-local guards for live
spec scope, archived task state, archive directory identity, retained evidence
refs, and archived Markdown links. The archive wrapper also protects existing
scenarios from accidental deletion unless the delta explicitly removes or
renames them.

This absorbs the useful `di-effect` archive-normalization and live-spec-diff
guard pattern. ETHOS adapts it to the terminal product by keeping the next
action under `ethos openspec --lifecycle --json` and by tying lifecycle health
to claims and evidence.

Alternative considered: trust official archive output alone. That leaves
repository-local product invariants unproved.

### Decision: Adopter Scaffolds Must Include OpenSpec Guidance

`ethos init` and `ethos adopt` must create an inspectable OpenSpec workspace:
config, README files, change templates, capability templates,
`specs/families.toml`, and profile-appropriate first capabilities. A bare
directory is not a complete governance substrate because it gives agents no
local routing grammar and no reviewable template for capability metadata.

This absorbs the useful productization stance from both reference
repositories: `di-effect` makes the OpenSpec workspace self-describing, while
`alphasim-dmgr` keeps public operation behind one `ethos ...` command plane.
ETHOS keeps both: scaffolded OpenSpec files are rich enough to guide work, but
the workflow still enters through ETHOS commands.

Alternative considered: generate only `openspec/config.yaml` and empty
directories. That optimizes first write speed while pushing the real product
friction into every future change.

### Decision: Context-Bound Mutation Is The Control Point

Every tracked write path must carry an explicit target root, expected checkout
role, and admitted path set. Manual `prewrite` calls remain a fallback, but the
terminal design must bind prewrite to mutation capability through hooks.

Alternative considered: rely on Git hooks. That catches commits, not wrong-root
writes, so it is too late.

### Decision: Progressive Disclosure Is A Documentation Requirement

Documentation must be layered from thin entrypoints to deeper references:

```text
entrypoint -> rule summary -> task-specific rule -> design/reference -> evidence
```

Agents should load the smallest sufficient surface first and expand only when a
task requires detail. Machine contracts remain in TOML, schemas, and command
JSON; Markdown carries judgment and explanation.

Alternative considered: put complete guidance in `AGENTS.md`. That makes every
agent pay the context cost for every rule and creates a stale parallel truth
store.

### Decision: This Lane Produces A Planning Substrate, Not Runtime Completion

The first pass may create `rules/` and `skills/` source surfaces because they
are design carriers and entrypoints. Runtime enforcement, digest validation,
projection generation, scaffolds, and package collapse belong in later tasks.

Alternative considered: make this lane finish the terminal implementation. That
would mix architecture, runtime migration, hook runtime, release, and scaffold
work into one unreviewable change.

## Risks / Trade-offs

- Over-documentation can recreate context explosion. Mitigation: entrypoints
  stay thin and every doc states its semantic duty.
- Adding `rules/` and `skills/` before full runtime support can look complete
  prematurely. Mitigation: OpenSpec tasks and design docs explicitly mark this
  as a planning substrate.
- Productized OpenSpec validation can become ceremony. Mitigation: validation
  focuses on ownership, lifecycle, claim/evidence binding, and archive
  correctness; narrative-only detail stays in docs.
- Capability facets can become a second taxonomy. Mitigation: facets are
  routing and review hints; exact live capability names remain the owner
  contract.
- Hook design without runtime enforcement still leaves a temporary bypass.
  Mitigation: name the bypass as a required later implementation task and use
  explicit `prewrite` plus explicit working directory in this lane.
- OpenSpec can become ceremony if used after the fact. Mitigation: require
  OpenSpec status/instructions before artifact writes in future lanes.

## Migration Plan

1. Land planning artifacts and target design in this Work Lane.
1. Use a later implementation lane to bind prewrite to mutation tools through
   context/pre-tool/pre-run/post-write hooks.
1. Use a later implementation lane to make OpenSpec preflight part of the lane
   admission or governance mutation command path.
1. Use a later implementation lane to implement capability-profile/family
   validation, proposal metadata validation, live-spec diff guards, archive
   closeout guards, and scaffold templates.
1. Only after enforcement exists, migrate terminal runtime topology and
   projections.
