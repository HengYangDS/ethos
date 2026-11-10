# Tasks

## 1. Name every audit refusal

- [x] 1.1 Print a refusal payload on contention and read it. Done when a contended run's stdout
      makes the captured decision name `dependency_audit_in_use`, an empty stdout names
      `dependency_audit_payload_missing`, and the test fails before the change. RED: a contended run
      printed nothing and the captured decision read `Expecting value: line 1 column 1 (char 0)`;
      GREEN in 0a0f83773, 00f6a46a9 and a2c8d165b: the contended stdout yields
      `dependency_audit_in_use`, an empty stdout `dependency_audit_payload_missing`, two refusal
      gaps both, and a malformed list `dependency_audit_refused`.

## 2. Acceptance

- [x] 2.1 Pass the precheck, the impacted sweep and readiness at the lane head. Done when each
      passes on the committed head. At 4280f49c1: the impacted tests ran 1,988 with one failure (the
      bounded-result-reader rule), fixed in a2c8d165b and rerun green, the static precheck passed,
      and readiness passed 28 of 28 gates.
