## MODIFIED Requirements

### Requirement: External Retirement Readiness
ETHOS SHALL determine whether an adopted repository can retire its embedded
ETHOS backend through generic repository profile, product-boundary, parity,
shadow, and lifecycle checks rather than product-core adopter directories.

#### Scenario: Retirement readiness is inspected
- **WHEN** `ethos fleet retirement-readiness --target <repo> --json` runs
- **THEN** ETHOS reads the target repository's `.ethos/profile.toml`
- **AND** validates declared binding roots such as `.config/`
- **AND** rejects profile-declared forbidden product-core adopter roots in the
  ETHOS product repository
- **AND** includes parity and shadow false-negative evidence in the verdict
- **AND** reports external-default, embedded-freeze, rollback-window evidence,
  and final retirement lifecycle gaps separately from parity and product-boundary gaps
- **AND** requires a tracked rollback-window evidence manifest with completed
  `proof_report`, `work_lane_closeout`, `domain_gate`, and `assistant_playbook`
  scenarios before accepting a terminal retirement-ready backend state
- **AND** requires the rollback-window manifest to be repository-local,
  Git-tracked, parseable, bound to reachable adopter and external-product
  heads, and backed by per-scenario evidence path, command, digest, target-head,
  and product-head fields
- **AND** does not require `adopters/<name>`, `profiles/<name>`, or
  `tests/fixtures/adopters/<name>` inside the ETHOS product repository.
