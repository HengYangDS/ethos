## MODIFIED Requirements

### Requirement: Governed transition commands fail closed on blocking verdicts

Every governed lifecycle command SHALL collect a typed request, invoke the one
transition reducer, and project its receipt or apply result. Commands SHALL NOT
reimplement policy, authority, effect ordering, recovery, or lifecycle state.

#### Scenario: Reducer reports a blocking or unknown verdict

- **WHEN** a public command receives a receipt whose verdict is not pass
- **THEN** it returns one structured result envelope
- **AND** performs no effect
- **AND** exposes the receipt gaps and exactly one continuation without a
  traceback

#### Scenario: Apply is requested

- **WHEN** a command applies a passing receipt
- **THEN** the command delegates the exact receipt to the common effect engine
- **AND** reports only the engine's post-observed result and Attestation

#### Scenario: gapped proof refuses through process status

- **WHEN** `ethos prove --expect-head <non-current-head> --json` runs
- **THEN** the shared result reports `verdict=block` and
  `expected_head_mismatch`
- **AND** the process exits non-zero because this is not a read-only reader view

## ADDED Requirements

### Requirement: Public results are one closed projection

CLI, Python, hooks, JSON, schemas, and agent surfaces SHALL project the same
result contract containing verdict, state, required gaps, receipt identity,
Attestation identity when present, and one continuation.

#### Scenario: Internal validation raises a known contract error

- **WHEN** a public surface encounters an invalid declaration, stale binding,
  unavailable runtime, partial effect, or failed external adapter
- **THEN** it returns a bounded typed result
- **AND** stderr and traceback do not become the machine-readable contract

### Requirement: Long operations are observable and resumable

Commands expected to exceed an interactive response window SHALL immediately
emit an operation identifier, receipt identity, phase, bounded log location,
and resume command. Terminal output SHALL bind the same receipt and exact result.

#### Scenario: A proof or migration continues after the first response

- **WHEN** the command is still running
- **THEN** the caller receives a running result rather than empty stdout or an
  apparent hang
- **AND** resume observes the existing operation instead of starting a duplicate

### Requirement: Command metadata has one owner

Cyclopts declarations and typed result contracts SHALL generate help, schemas,
remediation commands, skill projections, and transition graph metadata.

#### Scenario: Status names a next command

- **WHEN** status emits a remediation or continuation
- **THEN** the exact command exists in the same package help and accepts the
  projected arguments
- **AND** schema and human output describe the same result fields

### Requirement: Recovery is a public transition

Every partial or stale governed state that ETHOS can detect SHALL either have
one exact public derive/apply recovery path or remain blocked with a user
decision. Tracebacks, manual ref edits, SQLite edits, and hidden repair scripts
SHALL NOT be required.

#### Scenario: Ref, Lease, attachment, or proof binding is stale

- **WHEN** the reader recognizes an unambiguous recoverable relation
- **THEN** it emits the exact derive command and expected coordinates
- **AND** recovery reuses the common reducer and receipt contract
