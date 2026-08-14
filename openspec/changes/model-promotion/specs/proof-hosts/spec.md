## MODIFIED Requirements

### Requirement: Proof Separation

Local proof, hosted-only facts, and each provider observation SHALL remain
independent Attestations over the same receipt-bound contracts. No partial or
skipped proof SHALL be presented as full proof.

#### Scenario: Hosted context is absent locally

- **WHEN** a required hosted gate cannot execute in the current context
- **THEN** its state is `skipped` with the unavailable boundary
- **AND** the required proof verdict blocks rather than silently passing

#### Scenario: Conformance package is inspected

- **WHEN** tests inspect `proof-hosts`
- **THEN** it contains proof fixtures, topology matrices, and sample helpers
- **AND** runtime command and lifecycle semantics remain in their product owners

## ADDED Requirements

### Requirement: Required gate execution is explicit and complete

Every selected gate SHALL record `executed`, `skipped`, or `not-applicable`, its
command, environment contract, material digests, bounded outputs, and result.
Required plus skipped SHALL fail closed.

#### Scenario: One required gate silently exits without execution evidence

- **WHEN** the proof reducer cannot establish that the declared command ran
- **THEN** the gate is recorded as skipped or failed
- **AND** full proof is not issued

### Requirement: Authority and derived carriers change atomically

Profiles MAY declare repository-owned authorities and their derived carriers.
ETHOS SHALL compile consistency and Change-scope predicates through the existing
gate graph without hard-coding tool or provider semantics.

#### Scenario: Only a version authority changes

- **WHEN** a required derived lock, image, workflow, or test carrier is outside
  the same admitted Change or no longer matches
- **THEN** plan and prove block with the exact missing or drifting carrier

### Requirement: Terminal topology matrix is real

Conformance SHALL exercise single-person serial use, multiple worktrees,
multiple local processes, multiple hosts, optional candidate, local-only,
GitLab-only, GitHub-only, dual-peer, and multi-peer partial-success topologies
through real hooks and package-only executables.

#### Scenario: Topology conformance is reported

- **WHEN** the acceptance matrix completes
- **THEN** every cell identifies command, environment, source/target OIDs,
  receipt, effects, Attestations, and unverified boundaries
- **AND** fixture-only or source-checkout success cannot satisfy package-only or
  provider acceptance

### Requirement: Terminal proof binds the accepted runtime

Acceptance SHALL require fresh exact-HEAD full proof, official OpenSpec archive,
post-archive proof, signed governed land and accepted closeout, runtime
activation, install/readback, peer synchronization, housekeeping, SBOM, and
provenance receipts.

#### Scenario: Accepted runtime evidence is issued

- **WHEN** all local acceptance and declared peer obligations complete
- **THEN** one `accepted=true` source-independent receipt binds HEAD, tree,
  signature, wheel, runtime, entrypoint, schema, proof, install, SBOM,
  provenance, and readback hashes
- **AND** any missing obligation remains an explicit acceptance gap
