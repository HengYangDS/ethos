# Tasks

## 1. Readiness before admission

- [x] 1.1 Expose the readiness tier and let a gate graph run with settled results. Done when
      `run_gate_graph` given settled results neither runs nor reports them, returns every node in
      plan order, and the scheduler's tier is unchanged.
      (`test_settled_gates_are_neither_run_nor_reported` failed before and passes; every case of
      `test_public_proof_stops_heavy_work_after_readiness_failure` passes unchanged.)
- [x] 1.2 Run the readiness tier before the admission scope of a full executing proof. Done when a
      readiness failure ends the proof without entering the scope and leaves its test and package
      gates unrun with `gate_dependency_not_proven`, and a passing tier enters the scope once,
      after every readiness gate and before the first test or package gate, with no gate run twice.
      (`test_full_proof_waits_for_admission_only_after_readiness` and
      `test_a_full_proof_admits_its_tests_only_after_readiness` failed before and pass; 234 cases
      in the five proof, runner and slot modules pass.)

## 2. Documentation and specification

- [x] 2.1 Update the command-plane reference and the slot's module docstring. Done when both say
      that readiness gates run before the slot and the load wait. (`docs/reference/command-plane.md`
      and `src/ethos/adapters/gates/proof_slot.py` say so.)
- [x] 2.2 Write the `quality` delta. Done when strict validation and the cumulative archive
      simulation pass. (`openspec validate readiness-before-admission --strict` is valid, and
      `archive_readiness_gaps` on the lane's Change tree reports no gap.)

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
