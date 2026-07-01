## 1. OpenSpec And Contract Tests

- [x] 1.1 Add OpenSpec proposal, design, spec deltas, and tasks for Skills V2.
- [x] 1.2 Add failing tests for Skills V2 activation normalization and stable
      digests.
- [x] 1.3 Add failing tests for strict playbook checks rejecting placeholder
      skills.
- [x] 1.4 Add failing tests for legacy-compatible routing preserving v1
      adopter behavior.

## 2. Contracts And Schemas

- [x] 2.1 Add provider-neutral skill activation and package manifest IR under
      `ethos-contracts`.
- [x] 2.2 Add JSON schemas for skill activation, skill registry, and skill
      package manifests.
- [x] 2.3 Register new schemas in schema validation and focused tests.

## 3. Playbook Validation And Routing

- [x] 3.1 Normalize ETHOS v1, dmgr v1, and di-effect style activation records
      into the V2 IR.
- [x] 3.2 Add `legacy-compat` and `v2-strict` playbook check modes.
- [x] 3.3 Route changed-scope requests through changed-path evidence and V2
      routing metadata.
- [x] 3.4 Preserve existing JSON output fields while adding V2 enrichment.

## 4. Skill Package Quality And Projection Drift

- [x] 4.1 Add skill package manifest validation with package digest checks.
- [x] 4.2 Add official-quality `SKILL.md` checks for frontmatter, required
      sections, trust boundary, and evidence workflow.
- [x] 4.3 Add capability classification for command, script, MCP, and host
      projection surfaces.
- [x] 4.4 Report projection drift for package, registry, generator, and host
      metadata changes.

## 5. Scaffold, Report, Self-Audit, And Proof

- [x] 5.1 Update adoption scaffold to emit V2 skill activation metadata,
      package manifests, and official-quality skill content.
- [x] 5.2 Add Skills V2 scorecard data to `ethos report`.
- [x] 5.3 Add Skills V2 gaps to self-audit and proof gate output.
- [x] 5.4 Keep external adopter inspection in legacy-compatible mode during
      migration.

## 6. Product Root Migration And Evidence

- [x] 6.1 Migrate the ETHOS product-root skill package to V2 metadata and
      official-quality content.
- [x] 6.2 Update current docs after behavior is implemented.
- [x] 6.3 Run focused tests, parity checks, OpenSpec validation, Ruff, broad
      unit/architecture tests, and proof gates.
- [x] 6.4 Write dated evidence and claim only after verification passes.
