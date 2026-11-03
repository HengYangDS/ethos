## ADDED Requirements

### Requirement: Admission names a missing repository runtime

When the policy that proof admission compiles carries a `gate_runtime_missing:` gap, admission
SHALL report that gap instead of a policy mismatch, with a remediation hint that names the
repository's bootstrap verb in the admitted worktree.

#### Scenario: The candidate worktree has no repository environment

- **WHEN** a closeout audits a candidate worktree without a repository Python environment, and its
  committed policy runs a Python module gate
- **THEN** closeout is blocked with `gate_runtime_missing:repository-python`, not
  `proof_attestation_repository_policy_mismatch`
- **AND** its remediation names the bootstrap verb in that worktree.
