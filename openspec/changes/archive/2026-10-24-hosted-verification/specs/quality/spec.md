## MODIFIED Requirements

### Requirement: One test attempt provides reconstructable reports

The Python test owner SHALL emit JUnit, coverage and Allure results from one
execution. Allure 3 SHALL derive human and Agent views from those results without
rerunning tests. Missing, stale or incomplete required reports SHALL fail the
relevant test or hosted acceptance; rendering never changes a test verdict.

#### Scenario: A failed test still has a diagnostic report

- **WHEN** pytest records passing, failing and skipped cases in one attempt
- **THEN** Allure 3 can rebuild a human report and Agent query from the retained results
- **AND** the original pytest failure remains a failure

#### Scenario: Stale results cannot describe a new attempt

- **WHEN** a new test attempt begins or its source binding changes
- **THEN** old results and rendered views are invalidated
- **AND** missing or count-mismatched results cannot satisfy report admission

#### Scenario: Opaque parameters do not invent retries

- **WHEN** distinct pytest cases carry binary parameters with the same display representation
- **THEN** Allure retains their distinct logical test identities
- **AND** it does not present those cases as retries of one test

#### Scenario: GitHub execution is independent of workstation runners

- **WHEN** GitHub executes the selected quality workflow
- **THEN** its jobs select GitHub-hosted runners without workstation labels or inherited-hook overrides
- **AND** local emulation derives its platform mapping from the selected workflow job
- **AND** ephemeral hosted tool storage is not presented as cross-job persistence
- **AND** GitLab uses a separate digest-bound image, not an assumed runner-local cache

#### Scenario: Complete partitioned execution succeeds

- **WHEN** every required partition executes successfully against the selected source and policy
- **THEN** final admission requires their complete, nonduplicated result union and artifact validation
- **AND** the published wheel and SBOM bytes originate from that verified execution
- **AND** platform conformance and provider-only obligations retain their distinct execution

#### Scenario: External availability cannot starve repository proof

- **WHEN** an upstream link returns an adverse HTTP response other than temporary unavailability
- **THEN** the external-health observation remains nonpassing and retains its exact report
- **AND** the required repository proof and its JUnit, coverage, wheel and SBOM artifacts execute independently
- **AND** a failing upstream site is not presented as a valid link or a repository proof failure

#### Scenario: Temporary upstream unavailability is not a broken link

- **WHEN** an upstream link answers 503 Service Unavailable
- **THEN** the external-health observation accepts it as temporary unavailability
- **AND** a rate-limited or timed-out request is retried rather than accepted

#### Scenario: A link-checker diagnostic fails the link observation

- **WHEN** Lychee exits zero but writes a diagnostic to stderr, such as its hint that it followed a redirect
- **THEN** the link observation fails and retains the diagnostic
- **AND** the document links to the resolved target of the redirect instead

#### Scenario: Offline supply does not disable online assurance

- **WHEN** a hosted image prepares locked tool dependencies from its digest-bound cache
- **THEN** bootstrap performs no external fetch and leaves no job-wide offline flag
- **AND** network-required vulnerability checks may query their declared upstream and fail closed if unavailable

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
