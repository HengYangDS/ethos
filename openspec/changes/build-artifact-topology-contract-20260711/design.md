## Context

ETHOS already classifies `dist/` as a denied legacy generated home and
`build/artifacts/python/` as the semantic local-artifact home. The product's
full-proof gate nevertheless used the `uv build` default, so a correct build
could leave the repository in a topology-invalid state. The contributor guide
repeated the same producer command.

## Goals / Non-Goals

**Goals:**

- Make the proof gate's producer path agree with the topology contract.
- Make the contributor path identical to the proof command.
- Preserve the gate registry as the executable source and its packaged copy as
  the distribution projection.

**Non-Goals:**

- Do not add an artifact exception, cleanup-only fallback, or second build
  runner.
- Do not rewrite historical evidence or change remote publication behavior.

## Decisions

1. Keep one `build` gate and pass `--out-dir build/artifacts/python --clear`.
   The gate already owns package-build proof; adding a second post-build gate
   would duplicate the concern without improving the producer contract.
2. Change the contributor instruction to the exact same command. A human
   entrypoint is a producer surface and must not retain a divergent default.
3. Test both the typed gate graph and the contributor text. The first protects
   runtime behavior; the second prevents documentation from reintroducing a
   root-level producer.

## Risks / Trade-offs

- A local `dist/` directory from an earlier invocation remains denied until
  removed → remove that disposable residue after changing the producer, then
  prove the topology from a clean worktree.
- The packaged gate registry could drift from `system/gates.toml` → update both
  projections in one change and verify declaration parity through the existing
  configuration and full-proof gates.

## Migration Plan

1. Change the two gate declarations and contributor command.
2. Delete only generated, ignored `dist/` residue.
3. Run focused gate and documentation tests, then execute full proof at the
   resulting HEAD.

Rollback restores the prior declaration and command; it does not preserve
generated artifacts because they are disposable local state.
