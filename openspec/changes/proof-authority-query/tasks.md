- [x] **1. Declare the exact proof query.** Add one frozen transient query value
  and document applicability before currentness evaluation.
- [x] **2. Select before validating mutable dependencies.** Filter exact
  Commitment, operation, scope, plane, boundary, and floor; preserve integrity
  failures and same-query conflict detection.
- [x] **3. Bind candidate acceptance.** Construct the repository
  `candidate.accept` query from the candidate HEAD authority and use one query
  result for blocker reporting and plan compilation.
- [ ] **4. Prove positive and negative closure.** Cover retired historical Work
  Lane proof, wrong HEAD/repository/operation, stale applicable Lease, and true
  same-query conflict; validate OpenSpec and execute affected proof gates.

| Evidence | Tasks | Command |
| --- | ---: | --- |
| query and resolver properties | 1-2 | `pytest -q tests/unit/kernel/test_proof_plan_binding.py` |
| candidate acceptance contract | 3-4 | `pytest -q tests/unit/mutation/test_accepted_failure_matrix.py tests/unit/cli/test_contracts_closeout.py tests/unit/cli/test_contracts_land.py tests/unit/lanes/test_accepted_ref_admission.py` |
| declared model | 1-4 | `openspec validate proof-authority-query --strict --no-interactive` |
