# Design

## Context

The operation-catalog design (2026-11-07, draft 2, archived in the `rc-plan` Change as Appendix A)
places `ethos.application` between the surfaces and `domain` and orders the moves: proof first, then
the five shared operations, then the thin group bodies. Facts at the lane head:

- `ethos.domain` holds the five shared operations and their failure normalization
  (`domain/execution.py`, the `application_result` decorator), next to `prove.py`, `status.py`,
  `quality/` and `source_budget/`.
- `surface/cli/root/proof.py` (498 effective lines, ceiling 500) with `surface/cli/proof/host.py`
  and `surface/cli/proof/report.py` own proof. The body renders through `emit` at ten call sites,
  each of which ends the command, through `SystemExit` when the verdict is not `pass`.
- After the moves, the surfaces and `ethos.cli` import `domain`, `adapters`, `repository`,
  `normalization` or `assistants` along 69 direct edges, down from 99, and the remaining `domain`
  modules import `adapters` along 9, down from 69; `ethos.contracts` and `ethos.result` import
  nothing above them.

## Goals / Non-Goals

Goals:

- One owner for every public operation that CLI, MCP and the SDK share, proof included.
- Contracts that stop the lower-layer imports of the surfaces and of `domain` from growing.

Non-Goals:

- The catalog, the generic CLI adapter and typed steps (Changes `catalog-root` and
  `catalog-groups`), which retire the per-command modules and empty the surface exceptions.
- Moving the lane, hook, attestation and host command bodies: `catalog-groups` rebuilds those
  commands from catalog entries, so moving them now would move them twice.
- An MCP `prove` tool, which waits for `gate-environment`.
- Typed facts for `domain` (0.3.0), which empties its exceptions.

## Decisions

1. **Moves keep history and behavior.** `git mv` carries the five operations and
   `domain/execution.py` (as `application/invocation.py`); only import paths change, in product,
   tests and tools alike, including monkeypatch targets written as strings.
2. **Proof returns its result.** `application/proof/` receives the proof body as
   `prove_repository(root, request) -> EthosResult`, with `host.py` and `report.py` beside it.
   Each former `emit(...)` and `return` becomes `return result`, and the effect step that rendered a
   gap returns it. `ProofRequest` is the former `_ProofOptions` dataclass without Cyclopts
   annotations; the CLI flattens it with `Parameter(name="*")`, as today, and renders the result with
   `enforce=True`, which keeps every exit status. The operation binds `request.change` with
   `selected_change`, as the other operations do.
3. **Contracts as a ratchet.** The import-linter layers become `surface`, `application`, `domain`,
   `adapters`, `repository`. Three `forbidden` contracts follow the catalog design: the surfaces and
   `ethos.cli` import none of `domain`, `adapters`, `repository`, `normalization` and `assistants`;
   `ethos.contracts` and `ethos.result` import none of `application`, `domain`, `adapters` and
   `surface`; `domain` imports no `adapters`. Today's edges are listed as `ignore_imports`, and
   import-linter's default alerting on an unmatched ignore makes each removal shrink the list.
4. **The command reference and the rule follow the code.** `docs/reference/command-plane.md` names
   `ethos.application.*` and states that the CLI and the SDK reach proof while MCP waits for
   `gate-environment`; `rules/module-layout.md` §2.5 states the direction from `surface` through
   `application`, `domain` and `adapters` to `repository`.

## Risks / Trade-offs

- An SDK caller that imports `ethos.domain.plan` breaks. The SDK is not qualified for 0.2.0, and the
  changelog names the new paths.
- A string monkeypatch target that is not rewritten would silently stop patching; the full suite
  runs after the moves, and a search for each old dotted path must come back empty.
- The ignore lists are long (78 entries). They are transitional by design: `catalog-root` and
  `catalog-groups` empty the surface list, and 0.3.0's typed facts the `domain` list.
