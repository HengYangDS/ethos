## MODIFIED Requirements

### Requirement: Blocking Canonical Guidance Has a Repair Path

ETHOS SHALL admit corrective prewrite for an existing canonical OpenSpec spec
named by a current, valid official spec INFO finding. The source SHALL be the
selected active Change or a verified archive effect that owns that output.
Multiple findings for one spec SHALL map to one path. Admission SHALL retain
the actor, Lease, runtime, exact path and source bindings; it SHALL NOT satisfy
ordinary proof or commit admission.

#### Scenario: Exact canonical repair is reachable

- **WHEN** official validation reports a valid canonical spec with blocking INFO and the owning coordinated Work Lane requests prewrite for that exact spec file
- **THEN** ETHOS admits only that file for correction
- **AND THEN** ordinary proof remains blocked until fresh validation clears the finding.

#### Scenario: Archived Change repairs multiple findings in one output

- **WHEN** a verified native archive effect names the canonical spec, official validation reports two valid INFO findings in it, and the same coordinated Work Lane requests prewrite for that file
- **THEN** ETHOS admits that one exact path without recreating the active Change
- **AND THEN** ordinary status and proof remain blocked until fresh validation clears both findings.

#### Scenario: Unrelated or unsupported paths gain no authority

- **WHEN** the request includes an unrelated path, a missing or symlinked spec, a mismatched finding, invalid validation evidence, or a missing, mismatched or unverified archive effect
- **THEN** the finding grants no corrective prewrite for the unsupported path.

#### Scenario: Blocked status selects a repair action

- **WHEN** canonical INFO is the blocking gap for a coordinated Work Lane with an active Change or verified archived output
- **THEN** status names prewrite for one exact affected canonical spec instead of another status observation.
