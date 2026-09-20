## Context

The accepted CUE boundary is complete locally. The canonical terminal plan now
selects independent product delivery; this Change does not replace that plan.
Status and adoption already have mature lower-level owners, but their public
result composition lives inside CLI handlers. Runtime materialization and
selection still assume a Git common-directory installation.

## Goals / Non-Goals

Provide one transport-independent application path and a real installed stdio
MCP client journey, then migrate installation ownership without losing exact
repository selections. The first implementation slice exposes status and
adoption, with the remaining command family and installation lifecycle kept
explicitly incomplete.

No new lifecycle, broker, task database, global authorization cache or
agent-specific identity. Network serving and A2A remain separate optional
deployment boundaries, not prerequisites for local stdio.

## Decisions

- Move result composition to the existing domain layer, retaining its current
  Git, policy and effect owners. CLI only resolves native arguments and renders
  the returned EthosResult. SDK and MCP call that same operation directly.
  A subprocess CLI wrapper is rejected because it retains presentation coupling
  and adds parsing rather than removing it.
- Use official MCP SDK 2.2.0, verified against release commit
  9972c21aa42054fb1450c5fc614761ed11847ec6 on 2026-09-20.
  Its MCPServer and Client APIs replace hand-written protocol/session handling.
  The extra MCP CLI is unnecessary. Account for its transitive runtime closure,
  supported Python floor and package cost before activation.
- Bind one exact repository and the launcher process actor per MCP instance.
  Client arguments cannot select another root, change environment identity or
  turn an actor label into permission. Different repositories use independently
  bound instances over reusable installed bytes, not per-repository product copies.
- Preserve native SDK schemas and structured EthosResult. Protocol stdout carries
  only protocol messages; diagnostics use stderr. Unknown, blocked and successful
  application outcomes stay distinct from transport failure.
- Do not claim prompt cancellation from abandoning a thread. Native synchronous
  operations must finish or be drained before cancellation reports a completed
  boundary; interrupted mutations require existing post-observation/recovery.
  Prototype this behavior through the real client before enabling mutation tools.
- Host supply migration replaces the existing locator/materializer ownership,
  not its identity, live-use, rollback and exact selection guarantees. A symlink
  workaround or floating global executable is not the terminal design.

## Risks / Trade-offs

- The SDK brings async and HTTP dependencies even for stdio: measure the locked
  package closure; do not write an inferior protocol implementation to avoid it.
- Synchronous operation cancellation can delay acknowledgement: expose that limit
  until real cancellation/drain tests prove the stronger boundary.
- Source-only extraction can look complete while installation remains embedded:
  tasks distinguish shared API, protocol, artifact and installed acceptance.
- Existing tests reach CLI-local dependencies: migrate those consumers to the
  shared owner while preserving every distinguishing valid and failure case.

## Migration Plan

First extract existing operations with CLI/SDK parity and no duplicated behavior.
Then add the official protocol transport and real subprocess-client acceptance.
Next migrate shared host installation and exact repository version selection,
prove retained-state upgrade/rollback/exit, and only then reclaim replaced
common-directory generations. Each accepted boundary uses normal source proof,
current effect admission and installed readback; no dirty candidate self-activates.

Remaining proof-throughput obligations retain their original Change. Current
CUE local acceptance does not imply hosted qualification or complete CI reports.


## Shared Application Boundary Evidence

Status and adoption composition now belong to `ethos.domain.inspection` and
`ethos.domain.adoption`. Their CLI handlers retain argument/root resolution and
rendering only. Existing lower-level admission, repository and effect owners are
unchanged; no command subprocess, second parser or alternate verdict implementation
was added. Public source APIs require an explicit Path and return EthosResult.

The preserved direct-API tests were restored after accepted runtime acquired
context-complete command admission. The initial replay rejected the missing API
modules. The implemented slice passes 102 related adoption/reader/invalid-profile
cases and the native import-layer check. Direct reads do not write stdout or
change cwd; results agree with CLI verdict, gaps and next action. Adoption covers
valid, denied, stale, digest-mismatched and conflicting requests. Existing authored
profile, OpenSpec, agent and Forge content remains preserved. Duplicate fixture
setup was consolidated without deleting those distinct assertions.

These are source-level results, not installed SDK, MCP, complete command-family
or host-installation acceptance. The delivery tasks remain open. Original
preservation material remains until the restored content is committed and its
unique semantics verified; it is not another source of product authority.
