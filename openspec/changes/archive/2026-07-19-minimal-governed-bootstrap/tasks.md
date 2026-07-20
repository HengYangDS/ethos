## 1. Prove the minimal binding

- [x] 1.1 Replace complete-skeleton assertions with a failing test that default
  adoption plans and writes exactly `.ethos/profile.toml`.
- [x] 1.2 Prove the written profile is strict, valid, identity-bound, declares
  non-empty material paths, and activates the adopter profile.
- [x] 1.3 Prove strict conflict, empty-file replacement, default read-only plan,
  rollback and binding-detection reports remain correct for the one-file plan.

## 2. Delete the full scaffold

- [x] 2.1 Collapse adoption to one strict declaration and native TOML serializer
  with no template, manifest, or renderer taxonomy.
- [x] 2.2 Delete all optional templates, family/skill declarations, digest
  machinery, `.gitkeep` outputs and implicit provider generation.
- [x] 2.3 Delete byte digests, complete-skeleton tests and assertions tied only
  to retired outputs.
- [x] 2.4 Reconcile governance/readiness checks so adopter binding does not
  falsely claim optional capability readiness.

## 3. Validate and archive the Change

- [x] 3.1 Run focused adoption, profile, governance-kernel, CLI and
  external-adopter regressions with warnings as errors.
- [x] 3.2 Run Ruff, ty, Taplo/config checks, strict OpenSpec validation,
  Ponytail review and source-budget measurement; resolve every finding.
- [x] 3.3 Freeze the Claim and Chronicle against the final pre-commit index
  diff, including its digest and physical-line measurement; neither attests
  post-commit outcomes.
- [x] 3.4 Preserve the Change as the dated archive carrier.
- [x] 3.5 Declare the post-archive boundary: execute HEAD-bound proof for the
  exact archive commit before candidate land, accepted-root closeout and Work
  Lane retirement. Record those separate transitions outside this task list
  and do not push.
