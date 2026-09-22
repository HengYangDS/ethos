## ADDED Requirements

### Requirement: Complete verification throughput preserves assurance

ETHOS SHALL use 900 seconds as the temporary complete-proof acceptance threshold
on the declared reference workstation at a measured, qualified worker count.
The measurement SHALL include preparation,
all selected gates and cleanup, retaining at least 95-percent combined Python
line and branch coverage and every existing behavioral acceptance obligation.

#### Scenario: Complete performance acceptance

- **WHEN** an optimized exact-source full proof is measured
- **THEN** its elapsed time is at most 900 seconds
- **AND** all required gates pass without narrower acceptance or hidden prework
- **AND** cold-computation and warm measurements are identified separately

#### Scenario: More workers improve verified throughput

- **WHEN** identical inputs at a higher worker count preserve results and isolation
- **THEN** ETHOS may adopt the faster count and qualify the complete proof there
- **AND** the two-worker baseline remains a comparison, not an execution ceiling
- **AND** process-loss recovery remains a separately tested obligation

#### Scenario: Subsequent throughput improvement

- **WHEN** the temporary complete-proof threshold is met
- **THEN** ETHOS evaluates the 600-second direction using measured remaining work
- **AND** that optimization direction does not block otherwise qualified delivery
- **AND** neither infeasibility nor completion is inferred from local speedups

#### Scenario: Status reuses one observation but never stale runtime currentness

- **WHEN** public status projects workspace binding and hook readiness
- **THEN** both consume one fresh runtime observation for that invocation
- **AND** a later invocation independently detects changed selector or package bytes
- **AND** corruption blocks readiness and restoring valid bytes permits recovery
- **AND** mutation effects still obtain their own fresh admission

### Requirement: Test failure bounds pending verification work

Parallel verification SHALL bound per-worker queued work independently of suite
size. Worker loss or an ordinary assertion failure SHALL stop pending work,
retain its native diagnostic, and allow the surviving gate owner to reclaim
owned scratch without replay. Native failure history MAY prioritize cases but
SHALL NOT narrow the required collection or authorize success.

#### Scenario: Native worker exits with a large pending collection

- **WHEN** one worker exits while many collected cases remain pending
- **THEN** surviving workers drain only their bounded in-flight assignment
- **AND** the gate fails without re-executing the crashed case or recording success
- **AND** the surviving owner removes its owned basetemp

#### Scenario: All workers remain healthy

- **WHEN** the same declared collection runs without worker loss
- **THEN** every collected case executes exactly once and the gate succeeds
- **AND** equivalent-workload timing remains separate from failure latency

#### Scenario: An ordinary assertion fails with pending cases

- **WHEN** a test assertion fails before the declared collection finishes
- **THEN** workers drain only their bounded in-flight assignment
- **AND** the gate records no success and removes owned scratch

#### Scenario: Failure ordering is warm or absent

- **WHEN** native pytest failure history identifies a previously failing case
- **THEN** that case is scheduled before later ordinary work
- **AND** successful warm and empty-cache attempts each execute the complete collection once

### Requirement: Verification preparation preserves its measured subject

ETHOS SHALL complete the selected proof's required source-side checks before
behavior tests or delivery, including carrier ownership, repository/product boundaries, docs,
dependencies, formats and secrets. Test preparation SHALL preserve executing-module
identity across workers so coverage remains attributable. Initial generated-artifact
drift SHALL block expensive work; the same owner SHALL check post-execution drift again.

#### Scenario: Focused offline verification is selected

- **WHEN** the caller selects offline tests or the offline default proof
- **THEN** readiness ordering does not select otherwise unrequested online checks
- **AND** full proof and delivery retain their declared security requirements

#### Scenario: A selected online source check fails

- **WHEN** the selected proof includes an online source check that fails or is unknown
- **THEN** dependent behavior and delivery do not execute
- **AND** their results retain the failed prerequisite rather than claiming execution

#### Scenario: A transition lacks its required proof

- **WHEN** land or archive admission finds missing proof or only a weaker default proof
- **THEN** its continuation requests executed full proof for the exact subject
- **AND** explicit Change selection is preserved without an intermediate weaker run

#### Scenario: A source observer depends on executed behavior

- **WHEN** an observation transitively consumes test or package results
- **THEN** it remains downstream and does not become its own prerequisite
- **AND** a passing selected graph remains executable without additional gates

#### Scenario: A native adapter has no admitted carrier home

- **WHEN** the carrier gate rejects a candidate adapter's placement
- **THEN** the dependent test suite is not executed
- **AND** its result identifies the failed prerequisite without claiming execution

#### Scenario: Generated residue exists before verification

- **WHEN** the repository already contains generated files outside their admitted homes
- **THEN** repository audit reports the existing artifact owner's failure
- **AND** tests, coverage, packaging and installed acceptance do not start

#### Scenario: Verification creates new generated residue

- **WHEN** initial artifact observation passes but executed checks create misplaced output
- **THEN** the existing post-execution artifact gate rejects it
- **AND** early readiness is not reused as evidence of the later filesystem state

#### Scenario: Runtime supply variants share one test worker

- **WHEN** package and source supply fixtures run before runtime verification
- **THEN** the imported runtime module retains its original source identity
- **AND** subsequent executed verification remains observable to coverage

### Requirement: Hosted supply preparation precedes expensive verification

Hosted verification SHALL prepare its declared scanner, budget and SBOM supply
through the existing supply owners before starting proof. Preparation failure
SHALL preserve native diagnostics and exit status, invalidate previous attempt
reports, and produce a failed hosted observation without executing proof.
Package execution SHALL still validate supply in its own current environment.

#### Scenario: A declared tool cannot be prepared

- **WHEN** scanner, budget or SBOM preparation fails
- **THEN** expensive proof does not start and the native failure remains observable
- **AND** old proof, test and coverage reports cannot describe the new attempt
- **AND** the hosted receipt identifies failed supply without issuing an Attestation

#### Scenario: Prepared supply permits exact-source verification

- **WHEN** every required preparation succeeds
- **THEN** verification executes against the requested exact source
- **AND** the later package boundary retains its own executable validation

### Requirement: Native read batching preserves official semantics

ETHOS SHALL execute each bounded read batch through the selected official
OpenSpec package without copying its command parser or caching mutable results.
Every result SHALL bind its ordered input, native exit status and output.
Incomplete transport SHALL preserve failure evidence without claiming execution.

#### Scenario: An official command exits before the batch ends

- **WHEN** the native program exits during one read
- **THEN** completed frames preserve their native output and exit status
- **AND** unexecuted commands return an explicit interrupted result
- **AND** no effect command is admitted to the read batch

#### Scenario: A bounded output frame encounters pipe backpressure

- **WHEN** official output exceeds the receiving pipe's available capacity
- **THEN** the transport preserves every byte and input order as the reader drains
- **AND** retry remains bounded by the existing command deadline
- **AND** a stalled or closed reader fails without replaying a partially written frame
- **AND** native early exit still preserves completed output and marks the remaining tail

#### Scenario: Intent changes between public observations

- **WHEN** a later public plan observes changed OpenSpec inputs
- **THEN** it invokes the current official reader again
- **AND** an earlier successful observation cannot hide invalid current intent

### Requirement: Observation reuse preserves freshness and result identity

ETHOS SHALL reduce redundant computation using exact inputs and explicit
observation boundaries. Reuse SHALL preserve corruption detection and fresh
effect admission. Clearing derived caches SHALL change computation cost only,
not the verdict or selected effect.

#### Scenario: Relevant input changes

- **WHEN** source, rules, runtime, trust or coordinated state relevant to a
  decision changes
- **THEN** a prior cached result grants no current authorization
- **AND** only still-applicable immutable computation may be reused

#### Scenario: Complete source identity

- **WHEN** source includes staged, unstaged, untracked, deleted or executable-mode
  changes, including paths with index optimization flags
- **THEN** optimized observation preserves the native effective tree
- **AND** the caller's index and unrelated resources remain unchanged

### Requirement: Repository proof reuse preserves accepted meaning

Repository transitions SHALL independently validate each proof's source,
acceptance, policy, execution binding, integrity and applicability. Equivalent
accepted meaning may have distinct authoring and repository execution facts.
A prepared transition SHALL retain its carried proof identity and require that
exact proof to remain admitted; adding equivalent evidence SHALL NOT rewrite the
request or require repeating execution.

#### Scenario: Accepted authoring lane has retired

- **WHEN** an exact accepted source has a valid proof from a retired authoring lane
- **THEN** release preview and native ref admission use repository-transition proof semantics
- **AND** creating new authoring effects still requires current lane coordination

#### Scenario: A prepared release gains equivalent evidence

- **WHEN** another valid proof is recorded for the same accepted source and meaning
- **THEN** the original request and signed tag bytes remain reusable after fresh admission
- **AND** withdrawal, corruption, expiry or conflicting selected meaning still blocks

#### Scenario: Git reports failure around a ref effect

- **WHEN** the native ref process exits unsuccessfully
- **THEN** its command, working directory, output, exit code and plan/effect identities remain observable
- **AND** only a successful ref readback may classify the result as unchanged
- **AND** uncertain completion retains recovery intent without blind effect replay

### Requirement: Interrupted commands retain effect and process ownership boundaries

A synchronous command interrupted while its caller remains alive SHALL stop its
owned descendants before reporting completed cleanup. The original failure and
available output SHALL remain observable. Process-group control SHALL identify
its platform and containment limits; it SHALL NOT imply recovery after loss of
the supervisor or containment of deliberately detached processes.

#### Scenario: POSIX command timeout or caller cancellation

- **WHEN** a running command has a ready descendant in its owned process group
- **AND** its caller observes a timeout or cancellation
- **THEN** the group is terminated without signalling the caller's group
- **AND** inherited output pipes do not leave the descendant running
- **AND** the original exception and captured timeout output remain available

#### Scenario: Native executable verification times out

- **WHEN** a version-check executable has a ready descendant and exceeds its deadline
- **THEN** the shared process owner closes its process group before returning failure
- **AND** the verified archive and previous executable retain their existing protections
- **AND** transport and verification do not define competing cancellation semantics

#### Scenario: A test supervisor is killed

- **WHEN** a worker exits without executing its cleanup
- **THEN** a passing direct-command timeout test does not prove worker recovery
- **AND** native supervisor-loss and platform acceptance remain required

### Requirement: Runtime verification failure preserves generation ownership

A newly created runtime generation SHALL remain unaccepted until its required
verification succeeds. If verification fails or the caller is interrupted,
its creator SHALL remove that owned generation and propagate the failure,
without deleting or changing a previously accepted generation.

#### Scenario: Verification times out after the staging rename

- **WHEN** verification of a newly exposed generation times out or is interrupted
- **THEN** the failed generation and owned staging are removed
- **AND** the original failure propagates without claiming successful activation
- **AND** the previously accepted generation retains its exact bytes

### Requirement: Native metadata comparisons preserve observation semantics

ETHOS SHALL compare mutable file metadata before and after reading through the
same native observation channel. Path and open-handle observations SHALL refer
to the same file identity, without equating platform-specific timestamp meanings.
Unsafe kinds and replaced files SHALL remain rejected without leaking handles.

#### Scenario: Stable Windows path and handle timestamps differ

- **WHEN** path stat and descriptor stat expose different stable ctime meanings
- **THEN** unchanged native merge metadata remains readable
- **AND** changes within either channel or replacement of the named file are rejected
- **AND** read-induced access-time changes do not masquerade as content mutation

### Requirement: Verified supply survives later activation failure

The native supply owner SHALL retain an archive only after its declared digest
and executable member are verified. Later executable-version failure SHALL
preserve that verified download while leaving the previous executable unchanged.
Every reuse SHALL revalidate the archive; retained bytes do not grant acceptance.

#### Scenario: A downloaded executable fails its version check

- **WHEN** archive verification succeeds and executable verification fails or times out
- **THEN** exactly the verified archive remains available for a later attempt
- **AND** the old executable is unchanged and temporary preparation is removed
- **AND** retrying failed executable verification does not redownload the archive

#### Scenario: Archive content is invalid

- **WHEN** its digest, member identity or member type is invalid
- **THEN** the download is not retained as verified supply
- **AND** cached corruption remains rejected before executable activation

### Requirement: Owned removal minimizes permission effects

Runtime and test-output cleanup SHALL share one filesystem removal owner for
quiescent, exclusively owned paths. It SHALL prepare each real directory once
and modify only permissions required for deletion. External referents SHALL
retain bytes, permissions and modification time; caller-specific admission and
native failure reporting SHALL remain effective.

#### Scenario: Writable or sealed owned directories are removed

- **WHEN** an admitted tree contains writable or owner-inaccessible directories
- **THEN** cleanup removes the tree and changes only missing directory permissions
- **AND** POSIX regular-file modes are unchanged before unlinking
- **AND** repeated cleanup of the absent path succeeds

#### Scenario: Links or deletion failures occur

- **WHEN** an owned output contains a symbolic link or shares a regular-file inode
- **THEN** generic cleanup preserves external referents and runtime admission retains its stronger rejection
- **AND** a native deletion failure remains observable under the caller's declared policy

### Requirement: Archive preserves relative reference meaning

Archive projection SHALL resolve supported local Markdown destinations against
the exact source document and derive their archived or canonical locations.
Only destination bytes and declared source bindings may change. Recognition
SHALL reject missing or escaping targets, arbitrary edits and unsupported
reference semantics rather than certify unchanged bytes as unchanged meaning.

#### Scenario: Documents and delta requirements move

- **WHEN** official archive moves documents with repository and Change-local references
- **THEN** links, images and definitions retain their intended targets
- **AND** untouched text, code, titles and line endings remain identical
- **AND** canonical deltas use the locked official builder and derived source bindings

#### Scenario: Exact postimage or completion fails

- **WHEN** a referenced target disappears or a postimage contains unauthorized edits
- **THEN** recognition rejects that postimage before acceptance
- **AND** native effect failure preserves the existing compensation boundary
- **AND** repeated completed recognition performs no duplicate effect

### Requirement: Archive proof scope retains validated effect paths

A nonempty repository proof scope SHALL retain validated archive effect paths
that disappear from its net baseline diff. Source deletions SHALL remain
attributed independently of Git rename detection. Empty scope SHALL NOT select
unrelated historical archive authority.

#### Scenario: A Change creates and archives a document

- **WHEN** a source document is created and removed within the integrated range
- **THEN** postarchive proof still includes its validated effect obligation
- **AND** incomplete proof coverage remains rejected

### Requirement: Stable supply preserves the supported dependency closure

Supply updates SHALL select verified stable versions through their existing
owners and preserve the supported Python line. Native locks, package contents,
CI templates and generated projections SHALL agree. An incompatible upstream
release SHALL remain an explicit unresolved constraint, not an ignored dependency
or a false latest-version claim.

#### Scenario: Latest upstream conflicts with a required dependency

- **WHEN** the native resolver rejects a stable upstream version
- **THEN** the compatible closure remains selected and the exact conflict is reported
- **AND** other independently compatible updates continue through their normal acceptance

### Requirement: Quality capabilities initialize only when selected

Quality session discovery SHALL preserve its declared interface without loading
or validating unrelated capabilities. Each selected consumer SHALL resolve its
required tools and source-bound supply through the existing owners. A later
operation SHALL revalidate changed inputs; an already selected operation retains
its explicit input binding.

#### Scenario: An unrelated Node supply is unavailable

- **WHEN** native session listing or Python lint runs without prepared Node supply
- **THEN** the operation succeeds without resolving that unrelated capability
- **AND** a selected Markdown check rejects missing required supply

#### Scenario: Supply changes after one operation is selected

- **WHEN** a delivery operation binds valid supply and the configuration or lock later changes
- **THEN** subsequent selection rejects missing or mismatched supply
- **AND** the earlier operation retains its original explicit binding
- **AND** no prior successful validation authorizes the later operation

### Requirement: Hosted verification has one execution owner

A hosted attempt SHALL cover the declared quality dependency graph through its
shared execution owner. Native job partitions SHALL preserve every required
obligation, dependency and source binding. Compatible evidence MAY be reused
without repeating checks; aggregate-only forwarding SHALL NOT substitute for
actual execution or required artifact validation.

#### Scenario: Complete partitioned execution succeeds

- **WHEN** every required partition executes successfully against the selected source and policy
- **THEN** final admission requires their complete, nonduplicated result union and artifact validation
- **AND** the published wheel and SBOM bytes originate from that verified execution
- **AND** platform conformance and provider-only obligations retain their distinct execution

#### Scenario: A required result cannot establish success

- **WHEN** a result or required upload fails, is cancelled, skipped, missing, malformed or UNKNOWN
- **THEN** final admission cannot report success
- **AND** native diagnostics and available reports remain inspectable
- **AND** unchanged failure is not retried or hidden by a longer deadline

#### Scenario: Exact HEAD does not describe the executing source

- **WHEN** required source is missing from the selected commit or the worktree, index or policy drifts
- **THEN** exact-commit qualification is refused before execution or at the post-execution fence
- **AND** an exploratory working-tree observation cannot satisfy an exact-commit obligation

#### Scenario: A native tool reports an adverse diagnostic with exit zero

- **WHEN** native structured output contains a warning or error despite a zero exit
- **THEN** its owning adapter refuses success and retains the diagnostic
- **AND** informational output alone is not classified as a warning
- **AND** shell formatting and shell semantics are both checked by their declared native tools

#### Scenario: A proof check claims success with contradictory execution evidence

- **WHEN** a passing check carries a nonzero exit, warning, adverse diagnostic or required gap
- **THEN** shared execution admission refuses success before proof artifact creation
- **AND** normalization cannot erase the adverse signal to produce an admissible proof
- **AND** dependency scheduling and later proof validation use the same success predicate

#### Scenario: Unprivileged hosted link checking

- **WHEN** a prepared hosted checkout runs its full graph without system write access
- **THEN** link checking uses the declared locked binary wheel in that environment
- **AND** no separate installer writes host executable directories
- **AND** valid local links pass and missing targets produce a failing observation

#### Scenario: Specification validation has no ambient executable

- **WHEN** a prepared checkout has locked OpenSpec supply but no OpenSpec command on PATH
- **THEN** the gate invokes the existing verified official command resolver
- **AND** governance and gate consumers apply the same native result interpretation
- **AND** empty or informational valid results pass while invalid items, failed execution and unreadable output block
- **AND** missing official supply blocks without substituting another executable

### Requirement: Configuration selection preserves requested coverage

Configuration checks SHALL discover candidate files through native Git and
resolve their validation responsibility through the existing ownership compiler.
Explicit absent or differently owned targets SHALL NOT become empty success.
Default diagnostics MAY omit files deleted from the current candidate; exact
committed execution SHALL retain its independent source-correspondence check.

#### Scenario: A new configuration is outside the former filename list

- **WHEN** tracked or nonignored candidate configuration contains a native failure
- **THEN** default selection checks it and preserves the native failure
- **AND** ignored files and official external carriers remain with their owners

#### Scenario: The caller requests an absent or differently owned file

- **WHEN** an explicit target is missing, deleted or delegated to another owner
- **THEN** selection fails with the target and applicable owner guidance
- **AND** valid relative and absolute targets receive the same validation

### Requirement: Native tool supply has one declaration and bounded bootstrap

Development and CI SHALL consume the same mise tool selections and platform
locks. Ecosystem dependency locks SHALL remain with their package managers.
Observation SHALL NOT install tools. Provisioning SHALL preserve current
executables on failure, retain native diagnostics, and remove owned scratch.

#### Scenario: A clean runner has no mise installation

- **WHEN** the existing bootstrap executes with no prepared native mise
- **THEN** the version-bound official installer runs in owned staged storage with a deadline
- **AND** only a successfully verified executable is published
- **AND** preparation of locked gate tools completes before gate execution

#### Scenario: Operator-managed mise is newer than the declared minimum

- **WHEN** an existing stable operator executable meets the native minimum version
- **THEN** preparation reuses it without installing or replacing another executable
- **AND** staged bootstrap supply still requires its exact declared version
- **AND** older, prerelease, malformed or warning-bearing observations cannot pass

#### Scenario: Native Windows observation inherits another PowerShell's modules

- **WHEN** ACL or process observation starts native Windows PowerShell through an intermediate process
- **THEN** its child environment excludes the inherited module search path
- **AND** the parent environment, native error and timeout boundaries remain intact

#### Scenario: Native preparation fails or is interrupted

- **WHEN** download, archive validation, executable validation or execution times out or fails
- **THEN** the previous executable remains unchanged and owned descendants are drained
- **AND** unapproved version diagnostics prevent publication
- **AND** verified cache reuse preserves identity without repeating downloads

### Requirement: Native compilers preserve exact policy and projection inputs

CUE compilation SHALL consume the declared exact input closure and independently
compare generated outputs. CEL predicate declarations SHALL compile to Boolean
expressions. Candidate-supplied observations SHALL NOT certify candidate output.

#### Scenario: Candidate projection bytes agree with a forged local copy

- **WHEN** both copies disagree with the CUE source or candidate code supplies its own observation
- **THEN** the independent output comparison rejects the discrepancy
- **AND** staged admission uses index inputs rather than unrelated worktree bytes

#### Scenario: An expression cannot serve as a predicate

- **WHEN** a CEL declaration is invalid, unbound or not statically Boolean
- **THEN** declaration loading rejects it before runtime policy evaluation
- **AND** valid declared predicates retain their existing runtime semantics

#### Scenario: The bootstrap projection is edited independently

- **WHEN** installer bytes differ from the selected native generator output
- **THEN** the existing projection gate rejects the drift
- **AND** the documented lexical normalization and native shell formatting remain deterministic


### Requirement: Provider execution preserves the bound implementation

A proof binding repository provider source SHALL execute that source or a package
with the same source commit and tree. A mismatched invoking package SHALL be
rejected before any gate executes. Package-supplied adopter checks without
repository implementation bindings remain valid.

#### Scenario: Old runtime would mix with candidate toolchain

- **WHEN** a graph binds candidate provider source but the loaded package is older
- **THEN** execution reports the provider/source mismatch before external checks start
- **AND** no Attestation or passing host observation is produced
- **AND** recovery selects the admitted checkout's locked execution environment

#### Scenario: Matching execution and ordinary adoption

- **WHEN** providers execute from the candidate checkout or its matching package
- **THEN** ordinary gate execution remains available
- **AND** packaged-only adopter providers do not inherit a source-checkout requirement
- **AND** current effect admission and trusted-prior control replacement remain separate


### Requirement: Canonical decoding reuse preserves fresh observation

Attestation decoding reuse SHALL be keyed by exact bytes and bounded by total
retained input bytes. Large valid members SHALL remain reusable within that
budget. Oversized or evicted members SHALL still validate. Current membership,
source, Lease and effect authorization SHALL NOT be cached as permission.

#### Scenario: Warm and evicted reads select the same meaning

- **WHEN** the same valid bytes are read cold, warm or after eviction
- **THEN** the reader returns the same validated meaning without repeated warm decoding
- **AND** changed or deleted refs remain observable on every read
- **AND** corrupt replacement bytes cannot inherit an earlier valid member identity
