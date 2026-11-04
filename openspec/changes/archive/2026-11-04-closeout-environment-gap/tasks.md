# Tasks

## 1. Admission

- [x] 1.1 Report the runtime gaps of the compiled policy before the floor comparison. Done when
      admission of a passing proof from a root whose compiled policy lacks its repository runtime
      reports `gate_runtime_missing:repository-python`, and the new test failed with
      `proof_attestation_repository_policy_mismatch` before the fix.
- [x] 1.2 Give the runtime gap a remediation hint. Done when `remediation_for_gaps` returns
      `repository_runtime_missing` with the bootstrap verb for it.
- [x] 1.3 Record the fix in the changelog. Done when the Unreleased section of `CHANGELOG.md` names
      it under Fixed.

## 2. Specification

- [x] 2.1 Write the `repository-governance` delta. Done when strict validation and the cumulative
      archive simulation pass.

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
