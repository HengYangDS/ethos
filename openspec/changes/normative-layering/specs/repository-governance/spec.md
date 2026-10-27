## ADDED Requirements

### Requirement: Control-replacement receipts bind the trusted predecessor

For control replacement, the independent-verification request SHALL bind a
proof-floor digest of the complete replacement subject: the accepted
predecessor's commit, tree and control digest; the candidate's commit, tree,
control digest and executed proof Attestation; the changed control paths; and
any changed verification floor. A receipt issued for another predecessor,
control set or proof SHALL NOT admit the replacement.

#### Scenario: A receipt bound to another predecessor is rejected

- **GIVEN** a signed receipt for the candidate commit whose proof floor was
  computed against a different accepted predecessor
- **WHEN** control replacement evaluates that receipt
- **THEN** admission reports `independent_verification_receipt_binding_mismatch`
- **AND** the replacement is not admitted and no ref moves.

### Requirement: OpenSpec lifecycle applicability follows observed facts

ETHOS SHALL apply the official OpenSpec lifecycle to a governed repository when
an `openspec/` workspace exists, a Change is explicitly requested, or a changed
path matches the declared `[openspec].material_paths`. Without any of these
facts, plan and proof SHALL report the lifecycle state as `not_applicable`
without a required gap.

#### Scenario: No applicability fact is observed

- **GIVEN** a valid adopter declares `material_paths = ["docs/**"]` and has no
  `openspec/` directory
- **WHEN** plan runs without a requested Change on a change to `src/app.py` only
- **THEN** it reports the OpenSpec lifecycle state `not_applicable` with no
  required gap
- **AND** a change to `docs/guide.md` makes the lifecycle applicable.

### Requirement: CI runner and retained-step records own their commands

`.config/ci/runners.toml` MAY name, per Forge, the executables and references
that the Forge's CI runner provides beyond the repository toolchain and the
product runtime. Reference admission SHALL count them as owned only in that
Forge's own pipeline files, and a malformed record SHALL own nothing. A CI step
that the retention record keeps SHALL be owned by that record as a whole, so
admission reads no command names from it until its text changes.

#### Scenario: A runner executable is used by another Forge

- **GIVEN** `.config/ci/runners.toml` names `sha256sum` for `gitlab`
- **WHEN** only `.gitlab-ci.yml` invokes `sha256sum`
- **THEN** reference closure reports no orphan consumer for `sha256sum`
- **AND** once a GitHub workflow also invokes it, `sha256sum` is reported as an
  orphan consumer.

### Requirement: A replacement execution substrate is no weaker than its incumbent

A replacement execution substrate SHALL replace an adopter's incumbent only
after a proof Attestation binds the target root and HEAD, the product HEAD, the
compared command identities, the changed paths and the evidence-input digests,
and shows on that same subject that the replacement keeps every incumbent
blocking gap. It MAY add blocking obligations. A missing incumbent gap SHALL
block, even when reported as advisory, unless an admitted correction removes it.

#### Scenario: An incumbent gap becomes advisory

- **WHEN** the replacement reports an incumbent blocking gap only as an advisory
  signal on the same subject
- **THEN** the comparison records a comparative false negative
- **AND** no switch or removal effect is authorized.

### Requirement: A comparative correction rests on evidence outside the candidate

A replacement MAY drop one incumbent blocking finding only as a correction that
the retirement judgment admits. The correction SHALL name the finding, its
subject, the obligation it claimed to judge, and evidence from outside the
candidate: the repository's native tool on the same subject under its
previously accepted configuration, or a verifier admitted outside the candidate.
The replacement SHALL still judge that subject under that obligation.

#### Scenario: The candidate shows its own finding false

- **WHEN** an incumbent finding disappears only because the candidate changed
  its own Python target, exemptions or configuration
- **THEN** no correction is admitted
- **AND** the missing gap still blocks the transition.

### Requirement: A retirement judgment authorizes substrate effects

Switching, removing or rolling back an execution substrate SHALL be an exact-HEAD
and tree effect Attestation bound to a reachable Git recovery anchor, authorized
only by an accepted retirement judgment that records the capabilities that
transition, the surfaces the adopter keeps, comparative, profile and domain
false-negative evidence, each admitted correction, the deletion or retention
scope and the history that stays derived. A Git revert alone SHALL NOT be
recovery evidence.

#### Scenario: Removal rests on a revert

- **WHEN** removal of the incumbent is requested without an accepted retirement
  judgment, or with a revert commit as its only recovery
- **THEN** no effect is authorized
- **AND** the incumbent substrate stays in place.

### Requirement: Comparative proof refuses weakened evidence

A comparative proof SHALL block a replacement that accepts stale evidence,
treats a dry run as live proof, loses a domain gate planning obligation, or
permits removal while the adopter's declared documentation health is
unverified.

#### Scenario: A dry run stands in for live proof

- **WHEN** the replacement's compared result comes from a dry run of its
  commands
- **THEN** the comparative proof blocks
- **AND** it names the dry-run result as the gap.
