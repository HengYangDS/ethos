- [x] **1. Select authority before mutable dependencies.** Add one optional exact
  repository Commitment to the existing resolver; add no query entity or store.
- [x] **2. Bind candidate acceptance.** Resolve the candidate HEAD repository
  Commitment once and preserve its exact blocker result.
- [x] **3. Prove closure.** Cover historical Work Lane plus repository proof,
  wrong Commitment, generic ambiguity, and existing same-authority conflicts.

| Evidence | Tasks | Command |
| --- | ---: | --- |
| resolver | 1 | `pytest -q tests/unit/kernel/test_proof_plan_binding.py` |
| candidate acceptance | 2 | `pytest -q tests/unit/mutation/test_accepted_failure_matrix.py tests/unit/cli/test_contracts_land.py tests/unit/lanes/test_accepted_ref_admission.py` |
| declared model | 3 | `openspec validate proof-authority-query --strict --no-interactive` |
