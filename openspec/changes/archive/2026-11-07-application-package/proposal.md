# Proposal

## Why

Every transport should reach the same operations, but the operations have no owner of their own.
`inspect_repository`, `plan_repository`, `adopt_repository`, `land_repository` and
`publish_repository` live in `ethos.domain` beside the pure decisions that 0.3.0 separates, and the
proof operation exists only inside the Cyclopts command (`surface/cli/root/proof.py`), where it
renders its result at ten call sites, each ending the command, so MCP and the SDK cannot reach it.
The surfaces import the layers beneath them along 99 direct edges, and `domain` imports `adapters`
along 69. The 2026-11-07 expert committee's operation-catalog design (R2) makes `ethos.application`
the owner of every public operation; the catalog, store retention, peer identity records, release
predecessors and rehearsal admission are born there. A throwaway spike at 22:27 on 2026-11-07 drove
the real `land` preview, apply and closeout through a generic adapter built from catalog entries,
which the design required before this Change.

## What Changes

- A new package `ethos.application` sits between the surfaces and `domain`.
- `domain/inspection.py`, `domain/plan.py`, `domain/adoption.py`, `domain/land/` and
  `domain/publication/` move to `ethos.application` unchanged, and `domain/execution.py`, the
  failure normalization every operation shares, becomes `ethos.application.invocation`.
- Proof becomes an application operation, `prove_repository(root, request)`, that returns its
  result instead of rendering it; `ethos prove` renders that result with today's exit status. MCP
  `prove` stays out until proof gates run in an allow-listed environment (R8(c)).
- Import contracts: the layers gain `application`, and three forbidden contracts list today's
  exceptions, so the surfaces, the kernel contracts and `domain` can only shrink their lower-layer
  imports.
- The command reference names the new modules, and the module-layout rule states the new direction.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: application operations, proof included, are owned by `ethos.application`, and
  the surfaces may not add imports of the layers beneath it.

## Impact

- `src/ethos/application/` (moved and new modules), `src/ethos/domain/`, `src/ethos/surface/`,
  `src/ethos/cli.py` and every test or tool that imports a moved module.
- `.config/checks/import-linter/import-linter.toml`, `rules/module-layout.md` and
  `docs/reference/command-plane.md`.
- The SDK import path of the shared operations changes from `ethos.domain.*` to
  `ethos.application.*`; the SDK is not qualified for 0.2.0, and `CHANGELOG.md` names the move.
