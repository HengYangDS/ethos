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

Host qualification starts with the existing executable and native ACL checks,
before package construction. The Windows trust owner reads owner and access-rule
SIDs directly from the security descriptor; account names are not an intermediate
authority. Native execution retains missing environment, unavailable executable,
creation and timeout reasons instead of returning an ambiguous empty result.
This does not establish that a historical runner failure was caused by name
resolution: the full installed workload must pass on that exact native platform.

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

Adoption composes two owners: the typed ETHOS profile and official OpenSpec
configuration. Native configuration/schema/template observation belongs in the
adapter layer; pure repository policy consumes that observation. The shared
adoption adapter replaces the repository-local renderer and owns exact file
effects and compensation. CLI, SDK and MCP retain one application operation.

Use OpenSpec's own default and serializer, and compare generated bytes with its
CLI initializer. The native config-only first-Change probe succeeds without
directory anchors, so no `.gitkeep` files are projected. Existing YAML or YML,
custom schemas, context and rules remain authored inputs. Interpret them through
the official reader, schema resolver, rule validator and template loader; retain
warnings, including native root-selection warnings, rather than silently accept
dropped meaning. Template discovery alone
is rejected as readiness evidence. Host-global configuration is not an implicit
input. Native classification identifies externalized stores as unsupported by
this repository-bound operation, not invalid merely because host state is isolated.

Bind the selected configuration, schema and template bytes to the preview digest.
Re-observe at apply, check each write preimage, validate native postconditions and
preserve intervening content while attempting every independent safe compensation.
Standard exception groups retain the initiating and cleanup failures; cancellation
is not converted into a successful result. Individual replacements are
atomic; multi-file crash atomicity and hostile same-user concurrency are not
claimed. Generic governed-state fixtures declare their own inputs rather than
rerun onboarding; dedicated adoption acceptance executes the actual native path.

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

Status, planning, adoption, integration and publication compose results in their
existing domain operations. CLI resolves arguments and renders `EthosResult`;
SDK and MCP invoke the same typed operations with an explicit repository path.
Intent, admission, Git effects and evidence retain their existing owners. There
is no command subprocess, second parser or transport-specific verdict.

A published remote receipt does not authorize local proposal deletion. Pending
local refs retain the exact-root absorbed-ref continuation; replay observes
completed peer effects without repeating them. Remote retirement and local
retirement use one accepted-contribution observer. Native ancestry, verified
signature repair and conserved native refresh are admissible relationships;
patch similarity is not. Exact OIDs, topic role, absent Lease/worktree, fresh
observation and CAS remain independent conditions. Unknown conservation blocks
deletion.

Repeated accepted closeout observes refs, linked worktrees and the prior
Git-backed effect. The existing Attestation selector resolves identity and
ambiguity; aligned refs without a prior effect are an unattested no-op. Stale,
dirty or partially observed results retain recovery rather than new authority.
The shared OpenSpec transport and archive validator own setup: incomplete or
timed-out output cannot satisfy a native archive result, even if it resembles
complete JSON. Preserve their bounded execution and cleanup.

### Repository Identity Transition Boundary

Ordinary Git effects and Attestations require one profile-bound identity per
effect. An explicit typed rename instead binds the old and new identities,
object-database continuity, exact commits/trees, linear ancestry, each ref's
expected/desired HEAD, accepted intent and proof, actor and Lease generation.
Use the existing TransitionPlan, GitEffect, Attestation and CAS owners. The
authorization is one-use for one declared effect, not a global rename permit.

A new-identity work lane may first integrate into an old-identity candidate;
accepted and release transitions require separately admitted effects. Preserve
old-ID revisions as historical or untransitioned inputs, not current aliases.
Do not roll back the profile, rewrite history, infer identity from a shared
object database or silently widen the target set. New signed tags have no old
identity; an accepted mirror can contain separately described branch edges in
one declared atomic effect.

Preview preserves exact root, source, target and identity mode; a future signed
tag is not yet an exact effect. Replay observes the original result but cannot
authorize another movement. Reject stale refs, foreign object databases,
non-ancestry, forged relationships, missing proof, wrong actor and repeated
consumption through native positive and negative cases.

Ref completion is not checkout completion. If CAS succeeded but the linked
checkout still holds the exact preimage, recovery re-observes the original
effect, freshly admits the remaining file effect and preserves its Attestation.
Unrelated user edits block synchronization. Compare actual bytes with the
index without refreshing index bytes: stale stat metadata is not drift, while
unavailable observation is not cleanliness. Task 1.6 owns implementation and
task 4.2 owns installed qualification.

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

The official SDK MCPServer and standalone FastMCP are different implementations.
The isolated FastMCP comparison rejected undeclared root/actor fields in both
input modes and rejected a string Boolean in strict mode. Select locked FastMCP
with strict input validation, native registration, schema, resource and stdio
mechanics; delete manual Server callbacks. That comparison did not qualify
ETHOS effects, installed stdio, cancellation or recovery.

Bind one exact repository and startup-process actor per instance. Client
arguments cannot replace either binding or mint permission. Register the
existing typed application functions through native `FunctionTool.from_function`
and `add_tool`, avoiding the decorator path that failed on Python 3.12.
Retain real annotations and `EthosResult` serialization; MCP has no duplicate
signature, output-shaping rule, parser or task store. Protocol stdout is reserved
for MCP; diagnostics use stderr.

Instance-local middleware rejects changed process identity and serializes tool
calls. A deadline includes queueing and checks cancellation after synchronous
native work drains. Timeout, disconnect or lost ACK is not rollback; never
acknowledge complete cleanup while work can still mutate. This is not a
cross-process lock or forced-kill recovery. Existing effect-time admission and
post-observation remain authoritative; background framework tasks stay disabled.

One shared conformance workload exercises CLI, SDK and MCP against separate
disposable repositories: adoption, authorization refusal, stale input,
planned-byte identity, replay without inode/mtime change and reconnect. Installed
invocation uses its own interpreter. Source tests alone do not prove package,
native Windows, hard deadlines or unknown-effect recovery. Missing Git blocks
startup without contaminating JSON-RPC; a native observation timeout remains
UNKNOWN and requires observation. Preserve application verdict, malformed
request and transport failure as distinct outcomes.

An authorized new command declaration is not prior execution authority.
The existing patch/reference owner admits its declaration and rejects
undeclared consumers; do not solve this with alternate registration or a new
command registry. Complete real subprocess stdio, cancellation, disconnect and
installed-lifecycle cases before expanding mutation tools. Deliver the normal
CLI installation and version selection before optional MCP expansion.

## Host Console And Portable Distribution

The installed console selects the repository's verified CURRENT runtime;
explicit `python -m ethos.cli` uses the caller-selected package for development
or recovery. Hook installation may use the invoking product for an upgrade,
but ordinary operations never float with a host version. Invalid selectors or
payloads fail closed. No shell alias, adopter wrapper or copied parser.

Use the accepted relocatable interpreter plus exact locked-wheel image as the
portable runtime. Ordinary Homebrew framework Python needs an external
congruent interpreter for that image; the frozen experiment failed its
interpreter boundary. Neither experiment proves clean-host delivery. The
existing package owner builds reproducible archives from sealed bytes and
preserves the runtime manifest, wheel, modes and executable entry.

A Homebrew Cask projects the exact archive using native `command_wrapper`;
the formula experiment rewrote dylib identities and failed payload validation.
Cask extraction can add owner-write permission, so native preflight restores
sealed modes and revalidates the existing manifest before activation. A local
file URL is qualification input, not remote publication. Actual Homebrew
upgrade/uninstall and supported-platform journeys remain open.

Before repository activation, pin the validated runtime and wheel in one
user-owned content-addressed installation generation. CURRENT selects that
canonical path; two repositories may share immutable bytes but retain separate
hooks, state and selector CAS. A host lock, exact owner marker and same-parent
atomic exposure bound import and recovery. Removing the package carrier must
not break selected clients. Missing pinned supply blocks; it does not trigger
a floating host fallback or private rebuild.

When locked Python inputs change, publish and read back the trusted GitHub dev
supply image before updating its one CUE declaration and GitLab projection.
Independent peers have no cross-provider atomicity. Preserve repository-local
generations until every external selector and live consumer is proved migrated;
a digest-shaped directory is not deletion authority. Shared-store reclamation
and native package-manager exit remain separate acceptance obligations.

Sign native payloads before inventory and sealing; notarization submits that
frozen signed identity. Use the operator's existing native credential store
without embedding a project profile name or secret. Do not remove quarantine,
disable platform policy or infer a loader wait's sole cause from a ticket.
The publisher boundary below owns signer authorization; neither a successful
`--version` nor a mounted archive proves installed behavior.

## Publisher Identity and Release Authorization

Separate publisher identity, operator execution access, project release admission
and artifact evidence. Reuse the operator's existing credential authority and
native secret store; each project's release configuration carries only its own
public constraints and credential references. Do not embed this workstation's
team, certificate, profile, recovery path or another project's name in ETHOS.

For Apple delivery, Developer ID code-signing keys and notarization API keys have
different purposes. A Keychain profile is a locator, not an authorization rule.
Team API keys are not app-scoped: separate keys permit independent revocation,
not product isolation. Reuse a publisher within an admitted trust boundary;
separate access when hosts, maintainers, CI trust or revocation needs differ.
Do not infer trust merely because projects share an owner or operating-system user.

Secret-free builders produce candidates. A trusted release controller validates
the exact request and invokes fixed native signing operations, not candidate-owned
commands. Sign before payload sealing and bind transformed output to the original
admitted input. Keep per-project evidence, submission IDs and temporary resources;
serialize only genuinely shared mutable credential operations, not all builds.
Native protected environments help control access but do not by themselves
isolate a self-hosted runner. Verify the actual boundary with unauthorized and
cross-project requests before declaring release qualification.

Credentials remain provider-specific; this model does not make Apple keys valid
for Git, Windows or package-registry signing. Reuse existing release adapters
rather than adding a generic credential service. Local profile migration,
provider rotation and revocation have separate effects and recovery obligations.
The existing platform and release tasks own these implementation and acceptance
gaps; this design is not evidence that protected signing has been delivered.

References: [Apple API key scope][apple-api-scope],
[Apple notarization workflow][apple-notary-workflow] and
[GitHub execution environment limits][github-release-environments].

[apple-api-scope]: https://developer.apple.com/documentation/appstoreconnectapi/creating-api-keys-for-app-store-connect-api
[apple-notary-workflow]: https://developer.apple.com/documentation/security/customizing-the-notarization-workflow
[github-release-environments]: https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments

## Native Release Envelope and Execution Boundary

Native signing transforms an admitted disposable copy, never an installed
generation or original candidate. Reuse the existing materialization and manifest
owner to seal the changed bytes into a new identity. Do not add a signing
manifest, credential platform or arbitrary pre-seal command callback.

Select a notarizable, stapleable DMG for macOS release delivery. Retain portable
archives for internal qualification and other platforms. ZIP cannot itself carry
a stapled ticket for a standalone CLI; a flat installer package adds unnecessary
installer-signing identity and installation policy. Homebrew projects the exact
final native artifact. Submitted and stapled envelope identities differ without
changing the sealed inner runtime.

The signing domain must not run candidate Python, plugins or build commands.
Runtime publication and identity checks inspect sealed bytes without executing
them. Explicit runtime-execution qualification observes interpreter relocation
and product behavior in a credential-free target. The normal builder composes
these operations; no old combined check or generic callback remains. Publication
reports whether a generation was created or reused, so a later execution failure
can remove only newly created output, never a previously valid generation.

An isolated 2026-09-21 probe of accepted ddc213d58 re-signed 23 Mach-O files ad hoc.
Native verification passed; the old manifest rejected changed bytes; read-only
DMG mounting preserved the full inventory. Original bytes remained unchanged,
and the owned mount and temporary tree were removed. This establishes feasibility,
not Developer ID trust, sufficient entitlements, Gatekeeper or notarization.

This host deprecates hdiutil create and supports diskutil image create from.
Select by native producer capability without redefining the product's OS floor.
Preserve archive modes: the earlier data-filter probe changed file modes and
failed manifest validation before signing. Use the already-qualified exact
artifact extraction path, not relaxed manifest checks.

The existing distribution owner selects native macOS media through a `.dmg`
destination; internal qualification retains deterministic `.tar.gz` archives.
Native construction copies and revalidates the sealed runtime without executing
it, selects the available native image producer, and bounds creation time. A
creation failure does not retry a different producer or replace prior output.
Mounted inventory and wheel-byte checks qualify this carrier transformation,
not signing, notarization, installed behavior or release acceptance.

## Shared Installed Supply Activation

Use the existing hook installation operation with an explicit runtime path as
the package-carrier input. The runtime and wheel are copied together into one
user-owned installation generation before CURRENT selects its canonical path.
CURRENT remains the single repository selector; local digest-only selectors
retain their existing behavior. The launcher reads only bounded location
fields; Python still owns manifest, platform, build and admission checks.

The supplied runtime must match the invoking/accepted product build, its carried
dependency lock and its exact wheel. Reject symbolic links, junctions, invalid
paths and altered payloads before selector or state changes. This is explicit
installation ownership, not permission to execute a path inferred from PATH,
an environment variable or another repository. No host-wide mutable selection,
catalogue, source-checkout copy or additional package manager is introduced.

Two independent repositories select the same pinned bytes while retaining
separate hooks, policy, state and selector CAS. Compensation restores the prior
selector exactly. Repository retirement observes the selected external identity
but never enumerates the host store for deletion. Removing the package carrier
after selection must leave pinned clients usable. Missing or replaced pinned
supply blocks use rather than floating to a host upgrade or silently rebuilding
a private copy. The native selector reader owns location parsing even when its
payload is unavailable. Actual package-manager uninstall and host-store
reclamation still require separate consumer-safe acceptance.

The retained predecessor migration probe preserves one live Lease and five
authored files while changing from repository-local to shared installed supply.
An old-runtime process retains its generation until it exits; a fresh cleanup then
removes that local generation. Rollback to the predecessor and reactivation of
shared supply preserve the same state. These are isolated native package
observations, not authorization to migrate unrelated repositories or evidence
that package-manager removal already protects shared consumers.

Implement in the existing selection, materialization, hook activation/observation
and launcher owners. Prove external selection, native launcher resolution,
exact rollback and non-deletion with focused counterexamples; then execute two
installed adopter paths, source proof and current runtime acceptance. Shared-store
reclamation and published Homebrew remain separate open tasks.

## Release Version And Artifact Boundary

VERSION is the single next product-release target. Unpublished source builds
may share it, but an accepted release identity is immutable even before remote
publication. Changed released semantics need a new version. Acceptance of
source, alpha distribution and stable delivery are distinct claims. Readiness
comes from supported journeys, not alpha age, branch name or commit count.

Public compatibility covers CLI arguments/exits/JSON, SDK, MCP and persisted
state. State-schema and protocol versions retain independent meanings. Compile
canonical SemVer and PEP 440 from one product version; pre-release channel
selection is explicit and cannot displace stable delivery. Do not jump to 1.0,
reset published numbering, add an epoch or use timestamps to hide identity
conflicts.

The current hash-bearing development version identifies exact source but has
no monotonic upgrade order and is not a PyPI release. Keep such builds on exact
selection and local qualification paths. Source commit/tree, wheel digest and
platform runtime digest prove provenance, not public version ordering. A future
development channel needs a demonstrated ordering contract.

Release preparation freezes accepted source and target, creates release-identity
wheels through the existing uv/Hatch builder, signs native payloads before
sealing and validates the delivered artifacts. The Nox build owner requires
clean exact source and applicable proof, builds from disposable archived Git
bytes, rechecks before output and removes failed temporary roots. Ordinary
builds remain non-releasing.

Install smoke selects one exact release wheel without rebuilding it, checks
source identity and uses the existing content-addressed package owner for the
offline lifecycle workload. Its separate release-smoke receipt records actual
invocation and artifact; neither construction nor smoke issues publisher
release acceptance. Missing, redirected or changed wheels fail before effects.

Record release identity only after observation. Publish immutable artifacts
and their matching signed tag after required installed acceptance, with
version-reuse rejection and per-peer interrupted-effect recovery. Adopters
validate selected package, manifest and platform without copying publisher
Attestations or minting a release during hook installation. Task 3.7 retains
public-channel and release-materializer closure. Check occupied registry
versions and existing local release Attestations live; an empty tag list proves
neither absence. Rollback of a selected runtime is not publication rollback.

Official references: [Python packaging versioning][release-python-versioning]
and [Semantic Versioning][release-semver].

[release-python-versioning]: https://packaging.python.org/en/latest/specifications/version-specifiers/
[release-semver]: https://semver.org/spec/v2.0.0.html
