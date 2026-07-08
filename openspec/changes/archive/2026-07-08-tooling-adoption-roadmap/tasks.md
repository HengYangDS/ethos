## Tasks

### Planning Carrier

- [x] Add forge provider contract for GitHub/GitLab mirror semantics.
- [x] Add tooling adoption roadmap covering CI, local emulators, format/lint,
      architecture/C4, tools, OpenSpec schema customization, Superpowers, and
      optional adapters.
- [x] Add horizontal dmgr/di-effect/ETHOS mechanism matrix covering provider
      CI, local emulators, format, lint, architecture, C4, evidence, runbook,
      MCP, release, task ledger, Superpowers, Nox, Pixi, Pants, and domain
      runtime boundaries.
- [x] Add OpenSpec change carrier and repository-governance delta.
- [x] Bind an active claim and chronicle evidence to the roadmap.
- [x] Extend `system/tools.toml` with planned provider/tooling adoption entries.
- [x] Run `uv run --package ethos ethos openspec --lifecycle --json`.
- [x] Run focused markdown, config, schema, docs-registry, audit, and report proof.
- [x] Run head-bound `uv run --package ethos ethos prove --execute --expect-head <head> --json`
      before reporting planning readiness.

### Follow-up Implementation Work Packages

- [x] Implement GitHub/GitLab provider template sources, tracked projections,
      and template drift checks.
- [x] Implement local GitHub and GitLab emulator wrappers with explicit hosted
      status non-claim evidence.
- [x] Activate provider syntax gates such as `actionlint` after config owner,
      runner, CI projection, and proof coverage land.
- [x] Implement C4/LikeC4 architecture projection and drift checks.
- [x] Activate selected P1/P2 quality, architecture, MCP, and runbook gates
      in this Work Lane after config owner, runner, CI projection, and tests exist.
- [x] Activate evidence-operation and ETHOS-native release supply-chain gates
      after owner surfaces and proof coverage exist.
- [x] Record external signing, image scanning, and vulnerability-adapter gates
      as deferred follow-up Work Lanes after tool supply and proof coverage exist;
      do not claim them as active gates in this change.
