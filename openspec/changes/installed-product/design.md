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

Status, planning, adoption, integration and publication composition belong to
`ethos.domain.inspection`, `ethos.domain.plan`, `ethos.domain.adoption`,
`ethos.domain.land.operation` and `ethos.domain.publication.operation`.
The integration operation retains distinct candidate, accepted and release effects,
trusted control replacement, exact coordinates and current admission. Their CLI handlers retain
argument/root resolution and rendering only; MCP binds those same operations.
Planning retains the existing intent, rule, gate and skill compilers. Known
native and profile failures share one application result boundary without
reinterpreting operation-specific adoption conflicts. Existing lower-level admission,
repository and effect owners are
unchanged; no command subprocess, second parser or alternate verdict implementation
was added. Public source APIs require an explicit Path and return EthosResult.

Publication observes confirmed remote effects separately from local proposal
residue. A remote receipt never authorizes local deletion: pending local refs
produce `retirement_pending` and the existing exact-root absorbed-ref retirement
continuation. After that separately admitted effect, receipt replay observes full
convergence without repeating completed peer effects. Missing, linked, leased or
unknown local state retains its actual boundary and does not erase remote success.

Remote retirement, local retirement and its compensation share the accepted
contribution observer under `ethos.adapters.repo.commit.conservation`. Native
ancestry, verified signature repair and conserved native refresh are the supported
relationships; patch similarity is not evidence. Existing rewrite owners still
validate provenance and native composition. Exact local/accepted OIDs, fresh
pre-effect observation, topic role, absent Lease/worktree and native CAS remain
independent requirements. Unknown conservation cannot become successful deletion.

Repeated accepted closeout is an observation of current refs, affected worktrees
and the original Git-backed effect, not a new identity-ref transaction. One
accepted-state observer serves preview and authorized retry; the existing
Attestation selector owns effect identity and ambiguity checks. A bootstrap with
aligned refs but no prior effect remains an unattested no-op. Dirty or stale
coordinates retain their ordinary admission and synchronization boundaries.
This does not establish recovery from a crash before Attestation persistence.

The preserved direct-API tests were restored after accepted runtime acquired
context-complete command admission. The initial replay rejected the missing API
modules. That initial replay passed 102 related adoption/reader/invalid-profile
cases and the native import-layer check. Direct reads do not write stdout or
change cwd; results agree with CLI verdict, gaps and next action. Adoption covers
valid, denied, stale, digest-mismatched and conflicting requests. Existing authored
profile, OpenSpec, agent and Forge content remains preserved. Duplicate fixture
setup was consolidated without deleting those distinct assertions.

Those initial checks were source-level results, not installed SDK, MCP, complete
command-family or host-installation acceptance. The delivery tasks remain open. Original
preservation material remains until the restored content is committed and its
unique semantics verified; it is not another source of product authority.

Acceptance setup also consumes the existing OpenSpec transport and archive-result
validator, rather than executing structured commands through a generic text runner.
The transport owns child-only telemetry/update opt-out and process cleanup. Callers
may tighten its 60-second bound; fixture archival retains its 20-second deadline.
Timeout output remains diagnostic even when it contains complete-looking JSON;
only completed, valid, exactly bound archive results permit setup to continue.

### Repository Identity Transition Boundary

Ordinary repository identity resolution reads each effect's HEAD, expected,
desired and asserted revisions and requires one profile-bound identity. Both
Git-effect admission and Attestation validation consume that rule. It is the
correct ordinary-CAS boundary; a profile rename must not weaken it implicitly.

An explicit typed transition must distinguish object-database continuity from
old/new profile identities, product/path names and historical commit identity.
Use the existing TransitionPlan, GitEffect, Attestation and CAS owners. Bind exact
commits/trees, old/new identities, linear ancestry, each target ref's expected and
desired heads, accepted intent and proof, actor and current Lease generation.
One-shot means one effect authorization, not one globally permitted repository
rename. A new-identity work lane may integrate into an old-identity candidate,
followed by separately authorized accepted and release transitions. Do not require
one identity across all governing or historical refs, silently expand a target
set, or treat a shared object database as identity equivalence.

Each completed target transition uses the new identity for its result. Old-ID
revisions remain historical or not-yet-transitioned stage inputs, not aliases or
obsolete names required in the renamed product's current surfaces. No temporary
profile rollback, compatibility table or history rewrite is permitted. Recovery
observes the original effect and result before any retry; replay may report
completion but cannot consume that authorization for a second effect. A later
target transition requires its own fresh authorization and exact coordinates.
Acceptance must falsify stale/ref races, foreign object databases, non-ancestry,
forged relationships, missing proof, wrong actor, partial execution and repeated
consumption. Official task 1.6 owns this implementation and its native acceptance;
task 4.2 owns exact-source proof and installed delivery qualification.

The identity edge is narrower than the complete ref program: a newly created
signed tag has no old repository identity, while an accepted mirror can contain
two independently described branch edges in one declared atomic effect. Keep
new tags and unchanged-identity refs in that original program without fabricating
migration edges. Identity transitions refine integration and release operations;
they do not authorize unrelated ref mutation.

Preview preserves the selected root, source, target and identity mode in its
continuation. Tag preview admits the branch scope and declares that the future
signed object is not yet an exact effect. Replaying a completed accepted request
recognizes its original expected/desired coordinates and Attestation; that
observation cannot authorize another ref movement or accept invented coordinates.

Ref completion and checkout materialization are distinct postconditions. An
integration request whose ref CAS completed but whose linked checkout retains the
exact preimage remains pending, not current. Recovery validates the original ref
result, freshly admits the remaining file effect and uses the existing worktree
synchronization owner. It preserves the original ref Attestation and refuses
unrelated user edits rather than granting blanket dirty-worktree permission.
The mutation admission owner binds that preimage; execution rechecks it and the
application projection does not independently reinterpret the same dirty flag.

Content admission compares actual bytes with the index without refreshing index
bytes. A stale Git stat cache is not content drift; unavailable or malformed
observation is not cleanliness. Candidate, accepted and release consumers share
that observation boundary instead of accumulating separate recovery heuristics.

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
Register the callable through native FunctionTool.from_function and add_tool,
not the decorator's version-dependent inspect.isroutine dispatch. Actual Python
3.12 installation rejected that decorator path even though Python 3.14 passed.
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

Source tests and install-smoke consume one conformance workload. It creates
separate disposable repositories for real CLI, SDK and MCP adoption, verifies
authorization and stale-request refusals, checks exact planned bytes and
unchanged inode/mtime on replay, then reconnects. No existing adopter is mutated.
The installed invocation uses its own interpreter in isolated mode; the test
driver is not a product-source dependency. Wiring checks are not acceptance.

Known native-process failure meaning belongs to the shared application boundary,
not a transport. Root-bound operations preserve their signatures and return the
same typed failure as CLI startup. Missing capability remains BLOCK; a native
Git observation timeout is UNKNOWN and requires observation, not repeated
mutation. CLI alone selects the output stream and retains failure exit status.
On POSIX, the shared workload withdraws and restores a private Git locator after
MCP initialization, checking CLI/SDK/MCP agreement and same-server recovery.
That fault injector does not qualify native Windows or installed timeout/unknown
effect recovery. Controlled timeout regressions and real cancellation, lost-ACK
and forced-disconnect acceptance are distinct obligations.

Protocol stdout remains reserved during startup failure as well as connected
calls. The existing CLI output owner sends MCP diagnostics to stderr. Console
selection and direct module dispatch consume the same native-process failure
projection, preserving Git-specific recovery and evidence without a second
exception classifier. Missing Git must fail startup, not bypass repository
selection or emit ordinary CLI text into JSON-RPC. The installed workload checks
that negative boundary before connecting normally; startup checks alone do not
establish mutation, unknown-effect recovery or cancellation acceptance.

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

## Host Console And Portable Distribution

The installed console entry selects the target repository's verified CURRENT
runtime before invoking the existing command implementation. Explicit
`python -m ethos.cli` runs the caller-selected package for development and recovery.
Hook installation intentionally uses the invoking product to prepare an upgrade;
ordinary observations and effects cannot silently float with a host upgrade.
Invalid selectors and altered payloads fail closed, rather than fall back to the
host version. No shell alias, adopter wrapper, copied parser or new lifecycle.

Select the existing relocatable interpreter plus locked-wheel image for native
distribution. Ordinary Homebrew framework Python is insufficient for the current
image-construction contract without an external congruent interpreter; the earlier
installed experiment could discover an existing uv interpreter. A frozen binary
also failed the interpreter ABI boundary. Neither experiment proves a clean-host
product. Reuse the already accepted portable image and retain its exact wheel,
not another build/runtime implementation or dependency resolver.

The existing install acceptance owns archive generation after its complete
package lifecycle. Normalized archive metadata permits reproducible bytes without
changing the payload manifest. A generated Homebrew Cask installs that exact
archive with native ownership and its source/platform identity; local file URLs
are qualification input, never a claim of remote publication. Keep the immutable
payload outside the shell entry and preserve its hash-bound permissions.

This delivers distribution mechanics, not shared version-store migration.
Repository-local copies remain until the existing selection, activation and
retirement owners support shared immutable supply with exact repository binding,
concurrent activation, live-consumer fencing and safe removal. These incomplete
obligations retain their current tasks and cannot be checked from a working CLI.

Repository-local generations are not the terminal shared-supply store. A source
repository's worktrees and processes cannot prove that another repository's
`CURRENT` does not select an old generation. Preserve such unproven generations
until exact consumer migration to host-owned supply is observed; a digest-shaped
directory alone is not positive deletion ownership. After that migration is
qualified, reject new foreign selection of repository-local generations and
retire only resources with proved ownership and no live selector. This does not
weaken the independent package-manager consumer check for host-owned supply.

Accepted tests measured 49,999/50,000 ELOC. Distinct manifest-grammar,
cross-repository-selection and cleanup-recovery negatives bring this candidate
to 50,098 after shared-fixture consolidation. Removing them or compressing their
formatting would reduce assurance. The source-budget owner raises only the test
aggregate ceiling to 55,000; the product ceiling, 500-per-file limit and
95-percent coverage floor stay unchanged. No installed-product proof is implied.

The real formula experiment installed but rewrote native dylib identities;
preserve_rpath retained one extension but not libpython. Exact payload verification
rejected the result. Reject formula installation of prebuilt sealed images; use
Homebrew's native Cask command_wrapper and binary ownership instead. It preserves
the package's executable entry without teaching that entry to follow host symlinks
or introducing a hand-written shell wrapper. Caskroom/entry uninstall and native
platform acceptance remain required; basic --version does not prove payload integrity.

Cask extraction preserves file bytes but adds owner-write permission. Use native
structured preflight steps to restore immutable modes and call the existing
runtime manifest validator. Do not replace a manifest digest to accommodate
installer rewrites. For the standalone interpreter, use native codesign signature
and notarization requirements, not spctl's app assessment. The latter also rejects
the valid system ls executable; its rejection does not diagnose a CLI startup
failure. Signature integrity, notarization and actual execution are separate
claims. Follow Apple's [real installation test](https://developer.apple.com/forums/thread/130560),
including quarantine, rather than treating a static preflight as product acceptance.

The ad-hoc interpreter does not satisfy the native notarized requirement.
Resolve signing and notarization credentials from the operator's existing native
store and verify the exact consumer noninteractively. A metadata listing without
a match does not establish credential absence; do not copy credentials or encode
host-specific profile names in the product. Signing changes must precede payload
inventory and sealing. Notarization submission
uses the frozen signed payload; an outer notarization ticket is not runtime
authorization. Any payload change requires a new exact identity and new acceptance.
Do not infer the observed loader wait's sole cause from a missing notarization
ticket. No quarantine removal or platform-policy disablement is an acceptance path.
The qualification tap, failed installations and observed orphan process were
removed. Homebrew delivery, native platforms and shared-store migration remain open.

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

Use the existing hook installation operation with an explicit runtime path to
admit external immutable supply. CURRENT remains the single repository selector:
its digest line is unchanged; external selection adds one canonical absolute
runtime path. Local digest-only selectors retain their existing behavior. The
launcher reads these bounded location fields only; Python still owns manifest,
platform, build and admission checks.

The supplied runtime must match the invoking/accepted product build, its carried
dependency lock and its exact wheel. Reject symbolic links, junctions, invalid
paths and altered payloads before selector or state changes. This is explicit
installation ownership, not permission to execute a path inferred from PATH,
an environment variable or another repository. No host-wide mutable selection,
catalogue, source copy or additional package manager is introduced.

Two independent repositories can select the same external bytes while retaining
separate hooks, policy, state and selector CAS. Compensation restores the prior
selector exactly. Repository retirement observes the selected external identity
but never enumerates that external store for deletion. Missing or replaced supply
blocks use rather than floating to a host upgrade or silently rebuilding a private
copy. The native selector reader owns location parsing even when its payload is
unavailable. Recovery names the selected location; the operator restores it or
explicitly chooses new supply. The package-manager owner must still prove
live-consumer-safe upgrade/uninstall before its channel is qualified.

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

VERSION remains the single next product-release target. Several unpublished
source builds may share that target; an explicitly accepted release identity is
immutable even before remote publication, and changed released semantics require
a new version. Pre-release progression communicates
readiness, not commit count. Acceptance of source, alpha distribution and stable
delivery are distinct; do not infer product maturity from the accepted branch.

The compatibility surface includes public CLI arguments, exit codes and JSON,
SDK contracts, MCP tools and resources, and persisted repository state. State
schema and protocol versions retain their own compatibility meaning; do not bump
them merely because the product version changes. Define release maturity from
verified supported journeys, not the age of the alpha label. Do not jump to 1.0
or reset published numbering merely to make installation look complete.

The current development identity distinguishes exact source but provides no
chronological upgrade order: the successor 1b951028f sorts below c4d6de106 under
both native Python packaging and Homebrew comparisons. Keep such builds on exact
selection and local qualification paths, not an automatic publication channel.
Source commit/tree, wheel digest and platform runtime digest remain provenance;
they must not be substituted for public version ordering. PyPI does not accept
local version labels; the current +g...t... wheel is not an upstream PyPI release.

Use the existing identity compiler for canonical SemVer and its PEP 440
projection. Released channel metadata, signed tag and product display derive from
that one product version. A pre-release requires explicit channel selection and
must not displace stable delivery. Do not add an epoch, package-manager revision
or timestamp merely to conceal the current misuse of development identities.
If a future development channel is required, its ordering needs a separate
demonstrated requirement, not an implicit hash order.

Connect explicit release preparation to the existing build and admission owners:
freeze the accepted source and release target, construct release-identity wheels,
sign native payloads before sealing, then verify the exact delivered artifacts.
Record release identity after observation; publish immutable artifacts and their
matching signed tag only after required installation acceptance. No environment
flag, tag presence or renamed development wheel may bypass release admission.
A normal development build must remain non-releasing.

Publisher release acceptance and adopter runtime selection are different effects.
An adopter validates the exact package, manifest, platform and selected identity;
it does not need a copy of the publisher's Attestation set and does not create a
release claim during hook installation. Reuse the existing release identity
admission owner for same-version source and wheel conflicts across runtime targets.
Retain same-target closure uniqueness and selector CAS. Explicit installation
rollback remains distinct from forbidden publication rollback.

The existing Nox build owner accepts explicit --release --expect-head inputs.
It requires exact clean accepted source and applicable proof, archives those Git
bytes into a disposable source tree, and supplies the existing build-identity
carrier to the same uv/Hatch builder. Revalidate source and proof before projecting
the candidate wheel; failure removes temporary build roots and preserves previous
output. Ordinary builds remain development builds. Release construction is not
acceptance or publication.

The existing install_smoke session accepts the same explicit release arguments.
It selects one regular release wheel, verifies its exact source identity and
materializes it through the existing content-addressed package owner. The same
offline lifecycle workload verifies that artifact; it never rebuilds a substitute
or records publisher release acceptance. Recheck selected bytes before effects
and before producing evidence. A missing, redirected, changed or identity-mismatched
wheel cannot produce passing installation evidence.

Explicit release-candidate observations use build/evidence/local-install/release-smoke.json
without replacing the default development smoke receipt. Both retain their actual
build identity and invocation. This distinguishes qualification from release
acceptance; the remaining signing and native delivery obligations still apply.
The current acceptance work root is single-operation state within one checkout:
do not claim concurrent smoke execution or cross-project signer isolation from
this session's passing tests.

The explicit release materializer still has no production acceptance caller.
Connect it only after exact installed-artifact observation; do not manufacture an
accepted release merely to let a fresh adopter install it. Public channels still
need native version ordering, version reuse rejection, exact artifact/tag
correspondence and interrupted per-peer publication. These obligations remain in
task 3.7. Runtime rollback with preserved repository selection is distinct from
publishing an older version as a new release.

Official references: [Python packaging versioning][release-python-versioning]
and [Semantic Versioning][release-semver]. Registry ownership and occupied public
versions require live checks before choosing the next published number. Include
existing local release Attestations: an empty Git tag list does not establish
that no release exists or that package registries are empty.

[release-python-versioning]: https://packaging.python.org/en/latest/specifications/version-specifiers/
[release-semver]: https://semver.org/spec/v2.0.0.html
