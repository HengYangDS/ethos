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

1. Keep one `build` gate and pass `--out-dir build/artifacts/python --clear
   --no-create-gitignore`. `uv build --all-packages` builds workspace packages
   concurrently; its automatic output-local `.gitignore` is a shared transient
   writer and races with `--clear`. The repository-level `build/` ignore already
   owns this boundary, so suppressing the redundant marker makes the producer
   deterministic without weakening cleanup or artifact placement.
2. Change the contributor instruction to the exact same command. A human
   entrypoint is a producer surface and must not retain a divergent default.
3. Test both the typed gate graph and the contributor text. The first protects
   runtime behavior; the second prevents documentation from reintroducing a
   root-level producer.

## Risks / Trade-offs

- A local `dist/` directory from an earlier invocation remains denied until
  removed → remove that disposable residue after changing the producer, then
  prove the topology from a clean worktree.
- The packaged gate registry or CI projection could drift from
  `system/gates.toml` → update each active command projection in one change and
  verify declaration parity through the existing configuration, projection, and
  full-proof gates.

## Migration Plan

1. Change the two gate declarations and every active command projection.
2. Delete only generated, ignored `dist/` residue.
3. Run focused gate and documentation tests, then execute full proof at the
   resulting HEAD.

Rollback restores the prior declaration and command; it does not preserve
generated artifacts because they are disposable local state.
