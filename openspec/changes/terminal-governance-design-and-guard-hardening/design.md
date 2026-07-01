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
1. Only after enforcement exists, migrate terminal runtime topology and
   projections.
