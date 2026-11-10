# Tasks

## 1. Name every audit refusal

- [ ] 1.1 Print a refusal payload on contention and read it. Done when a contended run's stdout
      makes the captured decision name `dependency_audit_in_use`, an empty stdout names
      `dependency_audit_payload_missing`, and the test fails before the change.

## 2. Acceptance

- [ ] 2.1 Pass the precheck, the impacted sweep and readiness at the lane head. Done when each
      passes on the committed head.
