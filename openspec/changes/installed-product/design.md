## Context

The accepted CUE boundary is complete locally. The canonical terminal plan now
selects independent product delivery; this Change does not replace that plan.
Status and adoption already have mature lower-level owners, but their public
result composition lives inside CLI handlers. Runtime materialization and
selection still assume a Git common-directory installation.

## Integrated Product Decision

Product delivery follows one chain: installed capability discovery and repository
context -> accepted OpenSpec intent -> typed application operation -> fresh
admission -> bounded effect -> post-observation -> result and continuation.
Research, interpretation, collaboration, delivery and actual-outcome obligations
remain in the canonical plan; this Change supplies their usable product boundary,
not a replacement lifecycle or a reduced compiler-only product.

Three identities remain separate: the selected ETHOS product, the governed
repository, and that repository's own build toolchain. Shared immutable supply
may serve multiple repositories, but a host upgrade cannot silently change their
selections or merge their mutable state. Missing selection is actionable, not
permission to run arbitrary checkout code or an ambient interpreter.

CLI, SDK, MCP and Skills are coordinated delivery surfaces. CLI renders human or
machine results; SDK exposes typed operations; FastMCP over the official MCP SDK
provides protocol/session mechanics; Skills teach discovery and safe use of those same
operations. Installed guidance includes its product identity, applicability and
links to the target's accepted intent, rules and current continuation. Discovery
does not grant authorization. Preserve authored adopter guidance, including
conflicts, instead of overwriting it with a product-owned tutorial.

Native macOS and Linux delivery are required. Windows is desirable, not a
prerequisite that delays those platforms; no native Windows claim follows from
POSIX tests or WSL. Architecture/OS baseline, executable relocation, permissions,
hooks, MCP, update and exit are verified per declared release target.

Homebrew is a required supported installation channel, not a package-builder
selection. Use native formula/bottle mechanics and one Homebrew installation owner;
do not write another package manager. The Python wheel remains the SDK artifact.
The current npm trampoline is not adequate product delivery: it delegates to
ambient uv/Python or a checkout. Remove that path after its real consumers migrate;
npm remains legitimate internal supply for official OpenSpec.

PyInstaller is an evaluated option, not an endorsed optimum. The actual frozen
package starts and adopts, but hook installation assumes sys.executable is a
Python interpreter. Correct that product/interpreter boundary independently of
builder selection. Its exploratory build also used foreign site-packages and
emitted a deprecation warning; that build is not a qualified release recipe.

Compare native Homebrew Python packaging, a portable interpreter plus wheel,
and a frozen/native bundle against the same delivered workload. Compare complete
dependency closure, cold/warm startup, size, hooks, MCP, SDK coexistence,
offline operation, interruption, upgrade, rollback, signing and cleanup.
One-file appearance, fewer Python lines and successful --help are not selection
criteria. No tool is adopted merely because another product uses it.

Existing mise/uv supply, CUE projection and quality owners remain below product
meaning. Execution engines, CEL policy evaluation, reports and telemetry belong
to their existing foundation/quality decisions; they must not become prerequisites
for basic installed use or parallel policy, execution or proof authorities.
A replacement must name deleted responsibility, preserved counterexamples,
operational cost and migration exit. Missing evidence calls for one bounded
comparison, not indefinite deferral or a speculative dependency stack.

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
- Select standalone FastMCP with strict input validation as the MCP framework,
  over the official MCP SDK. Native tools, resources, schemas and transport
  lifecycle replace manual Server callback assembly. Keep repository operations
  and effect admission in their existing ETHOS owners. The isolated 4.0.5
  comparison establishes input behavior, not installed-product qualification.
  Account for its complete locked supply and use only required capabilities.
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

First repair truthful root-bound continuation at the shared adoption owner:
preview requires review of the exact plan; successful application selects status
for the same root; conflicts, stale inputs and missing authorization retain their
different recovery obligations. The binding planner returns facts, not a competing
next action. Keep public result composition out of individual transports.

Then complete extraction with CLI/SDK parity and no duplicated behavior.
Then add the official protocol transport and real subprocess-client acceptance.
Next deliver the usable installed CLI through the common package workload,
deliver the native Homebrew channel and matched Skills/context, and migrate
shared host installation with exact repository version selection,
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

## Installed Entry Recovery

The adopter feedback identifies two distinct failures: immutable materialization
deletes the product console script, and no host-installed dispatcher provides
repository-selected execution in a fresh shell. Restore the POSIX image entry
through the existing relocatable console-script renderer, including its argument
and interpreter isolation rules. Installed version acceptance must execute that
entry rather than only `python -m ethos.cli`, so a deleted entry cannot pass.

This is a prerequisite, not host installation completion. Windows executable
relocation remains unverified and must not inherit a POSIX claim. The host
dispatcher still needs one official installation owner, exact repository
selection, independent versions, explicit-root handling, interruption recovery,
upgrade/rollback and live-consumer-safe removal. Do not install aliases or
adopter-local wrappers, create another Change, or edit existing immutable images.
The full product path and existing installation tasks remain required.

## Retained-Predecessor Installation Boundary

Matching source, lock and wheel identities establishes provenance, not installed
capability completeness. A predecessor materializer can construct a generation
from the new wheel while still deleting its console entry. The current reuse
fast path must not accept that generation solely because its manifest and
identities are internally consistent. Required native entry semantics belong
to the existing materialization and acceptance owners.

Rebuild an incompatible generation through the normal immutable-generation
path; do not patch its bytes, change its manifest or add an installation bypass.
Keep valid reuse cheap and preserve live-consumer-safe retirement. Acceptance
must exercise the retained-predecessor transition, then the public repair and
actual installed entry, rather than only a fresh installation using the new
materializer. POSIX requirements must not silently claim Windows qualification.

## Product Presentation Projection

Update meaning without replacing the original visual design. The poster retains
its broad whitespace, thin left continuity axis and dominant right aperture mark;
the social preview retains its left mark, right wordmark and quiet enclosing
frame. Preserve proportions, restrained palette and typographic hierarchy.
Replace only obsolete terminology, the fixed command sequence and the narrowed
product definition. Do not substitute dense feature lists or generic text panels.

Faithfulness preserves current product meaning and distinguishes terminal vision
from delivered capability. Clarity requires understandable wording and readable
relationships at the intended size. Elegance retains the original visual identity
and removes needless detail. All three are required; format/schema success is
not aesthetic acceptance. The preceding redesign was rejected and its presentation
task is reopened. The revised assets remain candidates pending aesthetic review.

SVG masters and native librsvg rendering retain the established PNG consumer paths;
they add no product authority or application dependency. Actual raster inspection,
source/output parity and hosted application are separate evidence boundaries.

The adoption continuation repair has six original RED cases, 95 focused GREEN
cases and six public subprocess CLI outcomes at the shared owner. Preview,
missing authorization, stale HEAD, stale plan digest, conflict and applied state
remain distinct; planner-owned next_action was removed. These source observations
do not complete package, MCP, supported-platform or installed-client acceptance.

## Strict Native MCP Boundary

The official SDK 2.2.0 MCPServer and standalone FastMCP are distinct high-level
implementations. The former's undeclared-argument observation cannot reject the
latter. An isolated FastMCP 4.0.5 in-process client comparison exercised eight
cases across flexible and strict modes. Both modes rejected undeclared root and
actor fields before the probe body ran; strict mode additionally rejected a
string Boolean, while valid typed output passed in both modes.

Select FastMCP with strict_input_validation enabled. Remove the proposed manual
Server callback assembly rather than layering both implementations. Reuse
FastMCP's native registration, validation, schema generation, resources and
transport handling; do not patch framework internals or maintain a second parser.
This comparison has not exercised ETHOS effects, subprocess stdio, cancellation,
recovery or packaged installation. Those remain mandatory acceptance boundaries.
The existing fastmcp-contract-probe.log records the observations.

Bind one exact root and the startup process actor. Verify framework-native
execution and concurrency behavior before adding an adapter. No cancellation
acknowledgement may imply completed cleanup while a worker can still mutate;
protocol cancellation is not proof of effect rollback. Existing effect-time
admission remains authoritative. The protocol
adapter keeps application verdicts distinct from malformed requests and native
transport failure. No global actor mutation, shell parser or task database.

The native resolver locks FastMCP and its transitive closure. Direct AnyIO and
MCP type imports are consumed by the thin protocol adapter, not a second runtime.
HTTP, crypto, telemetry and optional task facilities are not automatically
activated merely because a framework supplies them. Background tasks stay
disabled. Installation and native platform behavior require separate acceptance.

Root binding uses functools.partial over the existing application functions.
Their annotations must resolve at runtime: retaining actual public types avoids
a duplicated adapter signature or custom annotation resolver. EthosResult owns
omission of absent governance_context for all native serializers; MCP does not
maintain another output-shaping rule.

The instance-local middleware rejects changed process identity and serializes
its own tool calls. Native FastMCP/AnyIO synchronous execution drains before the
next call. A request deadline includes queueing and checks cancellation again
after native work drains; elapsed synchronous work cannot silently return
success. Deadline or disconnect means the result was not acknowledged, not
rollback. It is not a hard kill of native filesystem work, cross-process
exclusion or forced-kill recovery. No custom thread supervisor or task store.

The install-smoke owner runs a real client and server from the isolated installed
wheel, checks discovery, strict root rejection, SDK parity and a fresh process
reconnect. A unit test proving this probe is wired is not installed acceptance.

Deliver the normal CLI installation and its version selection, upgrade and
uninstall before expanding MCP beyond the current shared operations. Remaining
SDK extraction and optional protocol capabilities must not indefinitely delay
a usable CLI. Homebrew remains the required channel; do not substitute a shell
alias or checkout-relative launcher.

New command declarations and command consumers are distinct relations.
Patch admission must permit an authorized native declaration without treating it
as prior execution authority; undeclared consumers remain rejected. Repair this
distinction at the existing patch/reference owner, not through alternate
registration syntax, omitted checks or another command registry.

In-process checks do not qualify stdio, installed lifecycle or hard-deadline
behavior. Complete the real subprocess journey and retain every existing test
obligation within the test budget before requesting complete acceptance.
