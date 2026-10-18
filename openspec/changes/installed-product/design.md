# Design

## Context

ETHOS needs usable installed operations without a source checkout. Its existing
domain, admission, Git, runtime and evidence owners supply the foundation; this
Change connects their product delivery surfaces. The [proposal](proposal.md)
owns motivation and scope, and the capability deltas own observable requirements.
The [product contract](../../../docs/governance/product-design-contract.md) and
[terminal plan](../../../docs/plans/terminal-governance-product-design.md) retain
their broader authority.

Product delivery follows one chain: installed capability discovery and repository
context, accepted OpenSpec intent, typed application operation, fresh admission,
bounded effect, post-observation, result and continuation. Research,
interpretation, collaboration and actual-outcome obligations retain their existing
owners. Execution engines, CEL policy, telemetry and CI projection remain
supporting capabilities rather than prerequisites for basic installed use.

Product identity, repository identity and the repository's build toolchain are
independent. Multiple repositories can share immutable supply while retaining
separate selections, policy, state and hooks. Missing or invalid selection is an
actionable failure, never permission to execute ambient Python or checkout code.

## Goals / Non-Goals

**Goals:**

- Provide one typed application path to CLI, SDK, MCP and version-matched guidance.
- Deliver an installed CLI and a real stdio MCP client journey outside the source
  checkout, with explicit repository selection and recoverable effects.
- Support native Homebrew installation and required native macOS/Linux targets;
  claim Windows support only after its own native qualification.
- Migrate reusable immutable supply and real consumers before retiring their
  replaced implementations, bindings and generations.

**Non-Goals:**

- A second lifecycle, broker, task store, authorization cache or agent identity.
- Mandatory network serving, A2A or optional framework capabilities for local use.
- A toolchain copied from ETHOS into adopters, a floating host selection, or a
  required Windows target that delays macOS/Linux delivery.
- Treating source tests, package construction, discovery or installation as proof
  of publication, supported platforms or actual user benefit.

## Decisions

### Typed application and native adoption

Domain operations compose `EthosResult`; CLI resolves arguments and renders it,
while SDK and MCP call the same typed operations with explicit repository paths.
Existing policy, observation and effect owners retain their responsibilities.
A subprocess CLI wrapper would retain presentation coupling and add parsing,
so it is rejected. Skills project discovery and safe use rather than duplicate
command semantics or overwrite authored adopter guidance.

Adoption composes the typed ETHOS profile with official OpenSpec configuration.
Native configuration, schema and template observation belongs to the adapter;
pure repository policy consumes that observation. The shared adoption owner
controls exact writes, postconditions and compensation. Its continuation binds
the same root: preview requests exact-plan review, successful apply selects
status, and conflicts, stale input and missing authorization remain distinct.
The binding planner returns facts without a competing next action.

Use OpenSpec's own defaults, reader and serializer. Compare initialization with
the official CLI; project no directory anchors. Preserve authored YAML/YML,
custom schemas, context and rules. Native validation retains warnings, including
root-selection warnings, rather than silently dropping meaning. Template
discovery alone proves no mutation readiness. Host-global configuration is not
an implicit input; externalized stores are explicitly unsupported by this
repository-bound operation rather than classified as malformed user content.

Preview binds exact configuration, schema and template bytes. Apply re-observes
them, checks each preimage and validates native postconditions. Compensation
attempts every independently safe owned write while preserving intervening
content. Exception groups retain the initiating failure and cleanup failures;
cancellation is never converted to success. Individual atomic replacement does
not establish multi-file crash atomicity or protection from hostile same-user
concurrency. General governance fixtures declare their inputs; dedicated adoption
acceptance runs the actual native initialization path.

### Contribution and identity transitions

Local and remote proposal retirement consume one accepted-contribution observer.
It recognizes native ancestry, verified signature repair and conserved native
refresh; patch similarity supplies no such authority. Exact OIDs, topic role,
closed review, absent Lease/worktree, fresh observation and CAS remain independent
conditions. A remote receipt does not authorize local deletion. Replay observes
completed peer effects and retains the exact-root continuation for pending local
refs without repeating effects.

Repeated accepted closeout observes refs, worktrees and its prior Git-backed
effect. The existing Attestation selector resolves identity and ambiguity;
aligned refs without that effect are an unattested no-op. Incomplete, dirty or
unavailable observations retain recovery. Official OpenSpec setup and archive
validation use the existing bounded transport; incomplete or timed-out output
cannot establish an archive result even when it resembles complete JSON.

Ordinary effects retain one profile-bound identity. An explicit typed rename
binds both identities, object-database continuity, exact commits/trees, linear
ancestry, per-ref expected/desired HEAD, accepted intent and proof, actor and
Lease generation. TransitionPlan, GitEffect, Attestation and CAS remain the
owners. Authorization is one-use for one declared effect. A work lane may
integrate into an old-identity candidate; accepted and release transitions need
separate admission. Historical old-ID revisions remain recoverable without
current aliases or history rewriting. A new signed tag has no inherited old
identity, and an atomic mirror describes each admitted branch edge explicitly.

Preview preserves root, source, target and identity mode; a future signed tag is
not yet an exact effect. Replay observes the original result without authorizing
another movement. If ref CAS completed but its linked checkout still has the
exact preimage, recovery freshly admits only the remaining file effect and
preserves the original Attestation. Unrelated edits block synchronization.
Compare actual bytes with the index without refreshing it: stale stat metadata
is distinct from content drift, and unavailable observation is not cleanliness.

### Strict native MCP

Use locked standalone FastMCP over the official MCP SDK for registration,
resources, schemas and stdio mechanics. The SDK's MCPServer is a different
implementation; retaining manual Server callbacks would duplicate framework
responsibility. Strict validation preserves real annotations and native
`EthosResult` serialization. Register existing typed functions through native
`FunctionTool.from_function` and `add_tool`, preserving Python 3.12 compatibility.
MCP owns no additional signature, output rule, parser or task store.

Each instance binds one repository and its startup-process actor. Client
arguments cannot replace either or mint permission. Instance-local middleware
rejects changed process identity and serializes calls. Protocol stdout contains
only protocol messages; diagnostics use stderr. Application PASS, BLOCK and
UNKNOWN remain distinct from malformed requests and transport failures.

A deadline includes queueing. Synchronous native work must finish or drain
before cancellation acknowledges a completed boundary. Timeout, disconnect and
lost acknowledgement are not rollback; effects require existing post-observation
and recovery. This is neither a cross-process lock nor forced-kill recovery.
Framework background tasks stay disabled. An authorized command declaration
enters the existing patch/reference owner rather than a new registration path.

Use one conformance workload through CLI, SDK and MCP in separately bound
disposable repositories. It covers adoption, refusal, stale input, planned-byte
identity, replay preserving inode/mtime and reconnect. Installed invocation uses
its own interpreter. Missing Git blocks startup without corrupting JSON-RPC;
native observation timeout remains UNKNOWN. Real subprocess stdio, cancellation,
disconnect and installed lifecycle acceptance precede broader mutation exposure.
Optional MCP expansion does not delay the usable installed CLI.

### Immutable installation and Homebrew

The installed console selects the repository's verified CURRENT runtime.
Explicit module invocation selects the caller's package for development or
recovery; hook installation can use the invoking product for an admitted upgrade.
Ordinary operations never float with the host version. The existing relocatable
renderer owns the POSIX console entry and argument/interpreter isolation. Actual
acceptance executes that entry rather than only the Python module.

Source, lock and wheel agreement establishes provenance, not complete installed
capability. A retained predecessor can construct matching bytes while deleting
the required console entry. The materialization owner rejects that generation,
rebuilds it through the immutable-generation path, and preserves valid reuse.
It never patches a generation or weakens its manifest. Retained-predecessor
upgrade and public repair test a different boundary from fresh installation.
Windows entry relocation requires independent native evidence.

Select a relocatable interpreter with an exact locked-wheel image as portable
supply. Native Homebrew Python and a frozen bundle remain meaningful builder
alternatives, evaluated against dependency closure, startup, size, hooks, MCP,
SDK coexistence, offline use, interruption, upgrade, rollback, signing and exit.
Framework Python needs a congruent external interpreter for this image; a frozen
entry cannot be treated as a Python interpreter by hook installation. A foreign
site-packages build or successful help output does not qualify either approach.

Homebrew Cask projects the exact archive through native `command_wrapper`.
Formula/bottle relocation rewrites dylib identities and conflicts with sealed
payload validation; Cask avoids that transformation. Native preflight restores
sealed modes after extraction and revalidates the manifest. Homebrew remains
one installation owner, and the wheel remains the SDK artifact. A local-file
qualification does not establish the published channel. Remove the ambient
uv/Python npm trampoline after its consumers migrate; npm retains its legitimate
official OpenSpec supply role.

Explicit hook installation takes a validated package carrier, copies its runtime
and wheel into one user-owned content-addressed generation, then selects that
canonical path by CURRENT. Legacy repository-local digest selectors retain
their existing interpretation. The launcher parses bounded location fields;
Python owns manifest, platform, build and admission checks. An exact owner marker,
host lock and same-parent atomic exposure bound import and recovery without a
host-wide mutable selector or catalogue.

Supply must match the admitted invoking/accepted build, dependency lock and exact
wheel. Validate paths, regularity, payload integrity and executable modes before
changing selectors or state. Independent repositories may select the same bytes
while retaining separate hooks and CAS. Compensation restores the exact prior
selector without overwriting intervening state. Missing or replaced pinned
supply blocks use rather than selecting ambient executables or rebuilding
silently; even an unavailable payload retains native selector interpretation.

Package-carrier removal must leave selected clients usable. Preserve local
generations until all selectors and live consumers migrate, including predecessor
runtime/wheel recovery. Repository retirement observes external selection but
does not enumerate the host store for deletion. Shared-store reclamation and
package-manager uninstall retain separate consumer-safe acceptance. Native
selection may preserve incumbent domain hooks; runtime provenance never substitutes
for their enforcement or the adopter's full proof.

### Native trust and release envelope

Check native executable and trust prerequisites before package construction.
Windows reads owner and access-rule SIDs directly from security descriptors;
account-name resolution is not authority. Preserve missing environment,
unavailable executable, creation, timeout and ACL rejection as distinct outcomes.
Required macOS/Linux and optional Windows targets each qualify their actual
architecture, OS baseline, relocation, permissions, hooks, MCP, update and exit.
POSIX tests or WSL cannot establish native Windows behavior.

Publisher identity, operator execution access, project release admission and
artifact evidence remain separate. Keep secret values in the existing native
store and carry only public constraints and credential references in project
configuration. Developer ID signing and notarization API keys have different
purposes; a Keychain profile is a locator, and team API keys are not app-scoped.
Separate keys permit independent revocation, not product isolation. Shared
publishers require an admitted trust boundary; differing hosts, maintainers,
CI trust or revocation needs justify separate access.

Secret-free builders produce candidates. Trusted release adapters validate exact
requests and invoke fixed native signing operations on disposable copies, never
installed generations or original candidates. They execute no candidate Python,
plugins, build commands or arbitrary pre-seal callback. Sign before inventory
and sealing, bind transformed output to admitted input, and submit that frozen
identity for notarization. Preserve quarantine and platform trust policy.
Serialize genuinely shared mutable credential operations rather than all builds.
Protected provider environments alone do not isolate a self-hosted runner;
unauthorized and cross-project requests require actual boundary tests.

The existing materialization and manifest owners seal changed bytes into a new
identity. Byte-only publication checks remain separate from credential-free
execution qualification. Publication distinguishes created and reused generations
so failure cleanup removes only newly created output. Ad-hoc signature or mounted
inventory evidence does not establish Developer ID, Gatekeeper or notarization.
Platform credentials remain distinct from Git and package-registry authorities.

Select a notarizable, stapleable DMG for macOS release and deterministic portable
archives for internal qualification and other platforms. ZIP cannot itself carry
the stapled ticket; a flat installer package adds unnecessary signing identity
and installation policy. Submitted and stapled envelope identities differ while
the sealed inner runtime remains unchanged. Homebrew projects the final artifact.

Native construction copies and validates sealed bytes without executing them,
preserves archive modes, selects an available image producer by capability and
bounds creation. Host-specific tool deprecation never redefines the product OS
floor. Creation failure does not retry another producer or replace prior output.
Mounted inventory and wheel checks qualify the carrier transformation separately
from signing, installation and release acceptance.

### Shared quality and native formatting

Applicable shared gates derive from authored inputs and compose with native
adopter checks. Markdown selects documentation, formatting/lint and links;
official intent selects OpenSpec and its schema prerequisite. A local gate with
the same name cannot replace a shipped verifier or identity. Applicable default
roots include their dependency closure while focused diagnosis stays explicit.
Each repository retains its business meaning and native development workflow.

The product supplies locked official Node, Prettier, Markdownlint and Lychee with
their common policies to both source and installed consumers. Repository policy
adds checks without disabling or replacing the mandatory floor. Prettier owns
spacing and container layout with preserved prose wrapping; Markdownlint owns
semantic rules. Immutable evidence, external publisher sources and captured
originals retain their separate mutation boundaries.

Markdownlint consumes native YAML. A secure TOML parser's nested representation
is incompatible with the official linter's parameter interpretation; a vulnerable
downgrade is rejected. A thin IO adapter supplies exact named documents to the
unchanged native API with explicit configuration and no discovery, imports,
inline overrides or fixing. Native parsing and diagnostics remain upstream.
Local policy cannot omit inputs, suppress the mandatory pass or mutate through
a fix setting. Native nested parameters need actual-consumer acceptance.

The [Docs Registry](../../../docs/governance/docs-registry.md) owns the shared DR
identity, metadata, five-section rationale and execution-content contract.
Distinct visible authored rationale supplies each role; quotations, literals and
metadata alone do not. One registry serves profile-selected documentation roots
without an adopter parser or copied decision register. Mechanical conformance
does not judge the decision's soundness or establish present delivery.

Source formatting compiles existing carrier assignments over literal tracked and
non-ignored new Git inputs. Ruff, Prettier, Taplo, shfmt and SVGO retain their
native responsibilities. Dependency records, generated projections, foreign
inputs and immutable originals keep their owners. Preview, check and admitted
fix use the same native postimages; ignores and pragmas preserve exact bytes
without waiving independent semantic proof. Shared/local postimage disagreement
refuses before writing.

Native format is preview-only by default. Fix needs explicit authorization,
current HEAD and complete-patch prewrite admission. It re-observes source bytes,
modes and index, applies through Git and verifies exact postimages without
staging or changing HEAD. Missing inventory remains UNKNOWN; unsafe paths,
native parse failures and authority conflicts remain blocking. Nox format/check
and proof are projections of this owner, with independent behavioral, static,
syntax, provenance and documentation acceptance preserved. Optimizing repeated
pure decoding never replaces the fresh native Git reads required for admission.

### Release identity and artifact acceptance

VERSION owns the next product-release target. Unpublished builds can share it;
an accepted release identity is immutable before remote publication. Changed
released semantics need a new version. Canonical SemVer and PEP 440 derive from
one product version with explicit prerelease channels; persisted-state and
protocol versions retain independent meanings. Compatibility covers CLI
arguments/exits/JSON, SDK, MCP and persisted state. Stable readiness follows
supported journeys, not alpha age, branch names or commit counts.

Hash-bearing development versions identify exact source but have no monotonic
upgrade order and are not PyPI releases. They stay on exact-selection and local
qualification paths; provenance digests do not establish public ordering.
A development channel needs its own demonstrated ordering contract rather than
an epoch, timestamp or reset that conceals release conflicts.

The existing uv/Hatch and Nox owners build release-identity wheels from clean,
exact, disposable archived Git inputs after applicable proof. Recheck source
before output and remove failed temporary roots. Freeze source and target before
signing and delivered-artifact validation. Install smoke consumes one exact
release wheel without rebuilding, validates its source identity and executes
the existing offline lifecycle workload. Its receipt records invocation and
artifact; construction and smoke do not issue publisher release acceptance.

Observe acceptance before recording release identity. Publish immutable artifacts
with their matching signed tag, version notes and source only after required
installed acceptance, enforcing version-reuse refusal and independently admitted
peer recovery. Check occupied registry versions and local release Attestations
directly; an empty tag list proves neither absence. Adopters validate package,
manifest and platform without copying publisher Attestations or publishing a
release during activation. Same-version source/wheel disagreement remains a
conflict across targets; rollback of selection is not publication rollback.

### Product presentation projection

Update meaning while retaining the original visual design. The poster keeps
its broad whitespace, thin left continuity axis and dominant right aperture
mark; the social preview keeps its left mark, right wordmark and quiet enclosing
frame. Preserve proportions, the restrained palette and typographic hierarchy.
Replace obsolete terminology, the fixed command sequence and the narrowed
product definition without substituting dense feature lists or generic panels.

Faithfulness preserves current product meaning and distinguishes terminal vision
from delivered capability. Clarity requires understandable wording and readable
relationships at the intended size. Elegance retains the original visual identity
and removes needless detail. All three require acceptance; format/schema success
does not establish aesthetic acceptance. The revised assets remain candidates
pending the separate review retained by [task 4.3](tasks.md).

SVG masters and native librsvg rendering retain the established PNG consumer
paths without adding product authority or application dependencies. Actual
raster inspection, source/output parity and hosted application retain separate
evidence boundaries.

## Risks / Trade-offs

- FastMCP/SDK brings async and HTTP dependencies even for stdio. Measure its
  locked closure and use required capabilities rather than duplicate protocol
  handling to avoid the cost.
- Draining synchronous work can delay cancellation acknowledgement. Expose the
  actual limit and preserve unknown-effect recovery; stronger claims need real
  client and native-process acceptance.
- Shared immutable supply reduces copies but requires exact consumer and custody
  checks before reclaiming generations. Activation success survives deferred
  cleanup; unknown liveness never permits deletion.
- Native package extraction and signing can change modes or bytes. Revalidate
  the exact sealed identity at each transformation without relaxing manifests.
- Source, artifact, installed, hosted and published proof are separate planes.
  [Tasks](tasks.md) retain each unfinished acceptance; a local comparison cannot
  close a dependent delivery or authorize another repository's cutover.

## Migration Plan

1. Complete root-bound application extraction with CLI/SDK agreement, native
   adoption and existing reference, profile and incoming-selection consumers.
2. Compose current source through native integration, preserving peer work and
   fresh reads; qualify one signed source with full proof before packaging.
3. Run the exact installed CLI and real MCP workload outside the checkout,
   then retained-state upgrade, interruption, rollback and live-consumer exit.
4. Deliver native required-platform artifacts, matched guidance and Homebrew;
   qualify release identity and protected signing at their respective owners.
5. Migrate exact real-adopter and cold-CI bindings, verify equivalent or stricter
   behavior, and retire replaced controllers, config, locators and generations
   in that accepted batch. Preserve failed evidence and active recovery consumers.

Changes descended from `proof-throughput` retain their own task identities and
acceptance. Their archived requirements remain authoritative; this delivery
does not reopen the retired Change or substitute for hosted qualification.
Locked Python supply changes require trusted GitHub dev-image publication and
readback before updating the single CUE declaration and GitLab projection.
Independent peers have no cross-provider atomicity.

## References

- [Apple API key scope](https://developer.apple.com/documentation/appstoreconnectapi/creating-api-keys-for-app-store-connect-api)
- [Apple notarization workflow](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow)
- [GitHub execution environment limits](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [Python packaging versioning](https://packaging.python.org/en/latest/specifications/version-specifiers/)
- [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
