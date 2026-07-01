## Why

The terminal governance redesign needs a repository-native planning carrier
before more implementation work proceeds. The previous accepted-root and
wrong-root write incidents show that advisory rules and manual prewrite calls
are insufficient when mutation tools can bypass repository context and OpenSpec
planning.

## What Changes

- Capture the terminal ETHOS product design as a tracked architecture target,
  not as chat-only rationale.
- Add a thin `AGENTS.md` entrypoint that forwards to canonical docs, rules, and
  skills instead of carrying detailed operating semantics.
- Introduce first-pass `rules/` and canonical `skills/` source surfaces for the
  target design without claiming full terminal implementation.
- Add hook and guard design for context refresh, pre-tool write admission,
  pre-run command risk checks, post-write fuse behavior, Git fallback hooks,
  and CI/release proof hooks.
- Add the failure-frontloading principle: repeated late failures move upstream
  from incident to diagnosis, rule, hook, scaffold/template, then schema/default.
- Add documentation progressive disclosure so agents load small entrypoints
  first and only expand into deeper references when the task requires it.
- Record that OpenSpec planning must precede non-trivial tracked design,
  rules, skill-system, hook, and product-shape changes.
- Expand OpenSpec from a pre-mutation checkpoint into a product protocol:
  accepted specs, active changes, archive records, capability profiles,
  proposal metadata, task lifecycle, claim/evidence binding, and live-spec diff
  guards have distinct duties.
- Require adopter scaffolds to create inspectable OpenSpec workspaces with
  config, README files, change templates, capability templates, families, and
  profile-appropriate first capabilities instead of empty directories.
- Keep useful `di-effect` patterns where they fit ETHOS: capability-local
  profiles, families, direct routing, reuse stance, dynamic facets, live-spec
  diff guards, and archive normalization.
- Keep useful `alphasim-dmgr` patterns where they fit ETHOS: a single command
  plane, Work Lane aware lifecycle state, claim/proof binding, topic-scoped
  closeout evidence, and explicit no-hosted-claim boundaries.
- Keep this lane scoped to design, planning, and guard-hardening mechanism
  definition; it does not implement the terminal package collapse, complete
  projection generator, full hook runtime, or full scaffold system.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `ethos-repository`: subject=terminal-governance-open-spec-protocol;
  reuse=extend; change=repository-governance obligations cover OpenSpec-first
  planning, Work Lane write admission, hook placement, failure-frontloading,
  productized OpenSpec carriers, archive closeout guards, adopter OpenSpec
  scaffolds, and terminal governance design; facet:lifecycle=authoring,validation,archive;
  facet:surface=docs,schema,scaffold; facet:authority=docs,openspec,evidence,claim
- `ethos-cli`: subject=openspec-adapter-command-plane; reuse=extend;
  change=`ethos openspec --json` is the product adapter over official OpenSpec
  checks and ETHOS lifecycle review, not a second public command plane;
  facet:lifecycle=validation,runtime; facet:surface=cli; facet:authority=source,schema,openspec
- `ethos-assistants`: subject=progressive-disclosure-projections;
  reuse=extend; change=assistant and skill surfaces are progressively
  disclosed projections over repository truth, not independent truth stores;
  facet:lifecycle=authoring,validation; facet:surface=docs,skill;
  facet:authority=docs,openspec
- `ethos-contracts`: subject=context-bound-mutation-contracts; reuse=extend;
  change=contract requirements cover context-bound mutation admission,
  source-digested projections, and format/carrier boundaries;
  facet:lifecycle=validation,runtime; facet:surface=schema,cli;
  facet:authority=source,schema,openspec

## Impact

- Affected files: `AGENTS.md`, `docs/architecture/terminal-governance-product-design.md`,
  `docs/governance/openspec-governance.md`, `docs/index.md`, `rules/`,
  `skills/`, and this OpenSpec change.
- No runtime CLI, MCP, SDK, package, scaffold, hook, or projection-generator
  implementation is delivered by this change.
- The change creates design and task constraints for later implementation lanes
  to close the prewrite bypass and OpenSpec bypass as product bugs.
