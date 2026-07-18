## ADDED Requirements

### Requirement: Candidate-authoritative archived scope corrections are exact

ETHOS MAY preserve candidate content during a sanctioned Work Lane replay only
when a conflict exactly matches a prior archived, claim-bound policy correction
and the candidate index proves every declared implementation and regression
invariant for that correction. All other conflict sets SHALL remain fail-closed.

#### Scenario: archived source-budget scope correction is replayed again

- **WHEN** refresh-base encounters exactly the source-budget proof-scope
  implementation and regression conflict set
- **AND** an archived `quality:source-budget-proof-scope` claim and its archived
  carrier declare every conflicted path
- **AND** candidate stage 2 proves global-compression reporting and the
  default-versus-full source-budget proof-floor boundary
- **THEN** ETHOS SHALL preserve the candidate stage-2 files and continue replay
- **AND** it SHALL require normal post-refresh validation and HEAD-bound proof.

#### Scenario: full proof retains global source-budget evidence

- **WHEN** the candidate policy separates a fine-grained default proof from
  repository-wide compression closeout
- **THEN** the default proof SHALL omit `source-budget`
- **AND** the full proof SHALL retain `source-budget` without calling it local
  code correctness.

#### Scenario: candidate authority cannot be proved

- **WHEN** any exact path, archived claim, carrier promotion target, or candidate
  source/test invariant is absent
- **THEN** ETHOS SHALL NOT resolve the conflict automatically
- **AND** refresh-base SHALL retain its ordinary fail-closed result.

#### Scenario: semantic recovery and a parity projection coexist

- **WHEN** the same refresh also recovers a generated parity projection
- **THEN** only that generated projection SHALL populate
  `stale_projection_paths` and require regeneration
- **AND** the source-budget implementation and test paths SHALL remain in
  separately named semantic-recovery diagnostics.
