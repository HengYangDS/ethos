# Tasks

## 1. The cited record

- [x] 1.1 Write the plan as a proof artifact and issue the record in the cited form when its plan is
      too large to carry. Done when a proof of a lane with about 1,400 changed paths records under
      2,000 bytes at the unchanged bound, the plan read back through the record equals the plan that
      ran, and a proof of a small lane still carries its plan. (At `458d8b417`,
      `test_a_proof_over_the_bound_is_recorded_and_read_back` passes: with 1,400 changed paths the
      record that carries its plan is over 1 MiB, the writer returns the cited record of under 2,000
      bytes, and the plan read back through it equals the plan that ran.
      `test_proof_attestation_is_content_addressed_and_exactly_bound` passes on a small lane, whose
      record keeps the predicate `proof:execution` and its plan, and
      `test_a_proof_is_cited_only_above_a_third_of_the_bound` pins both sides of the threshold; a
      real proof of 450 changed paths, between a third and half of the bound, is cited
      (`test_a_proof_between_a_third_and_half_of_the_bound_is_cited`).)
- [x] 1.2 Resolve a cited plan and refuse each wrong case by name. Done when an absent file, altered
      bytes and a write over other bytes each fail closed with their own gap code, and selection and
      the repository-transition admission give the same answer. (At `458d8b417`,
      `test_d_plan_bytes_that_are_not_the_cited_plan_are_refused_by_name` passes in its four cases:
      an absent file gives `proof_attestation_plan_artifact_missing`; altered bytes, another plan's
      bytes and bytes that are no document give `…_digest_mismatch`; a write over other bytes gives
      `…_collision`; and selection and the repository-transition admission return the same gap. A
      further test covers bytes that match the digest and are no plan document:
      `proof_attestation_plan_invalid`.)
- [x] 1.3 Keep the by-value form readable. Done when a record written in that form reads and is
      selected with no plan file in the store. (At `458d8b417`,
      `test_c_a_record_that_carries_its_plan_is_still_admitted` and
      `test_c_both_forms_of_one_proof_select_one_record` pass, and the carried form's gaps for a
      missing plan, a plan of another digest and an envelope that names another plan are asserted in
      `test_proof_plan_binding.py`.)
- [x] 1.4 Carry the cited proof through a landing. Done when the product's archive, landing and
      closeout of such a lane, on a proof issued through the product's issuance, re-validate both of
      the landing's records whole. (At `458d8b417`,
      `test_b_a_landing_of_many_paths_keeps_every_record_under_the_bound` passes: the archive,
      landing and closeout of a lane with 1,400 changed paths, whose integration and acceptance
      records each carry the cited proof, validate whole through `validate_git_effect_attestation`
      and stay under the bound.)

## 2. Retention and the record of the change

- [x] 2.1 Teach retention the plan file's kind. Done when a plan file is kept while a record cites
      it and deleted only when its proof leaves. (At `458d8b417`,
      `test_f_plan_bytes_stay_while_a_live_record_names_them` passes, the retention apply test
      deletes an aged plan that no record names and tallies `proof-plan`, and a document with a key
      more, a key fewer or a version that is not the integer 1 stays unowned (`test_kinds.py`,
      `test_apply.py`).)
- [x] 2.2 State the change and its rollback limit in the changelog. Done when the unreleased section
      names the cited form, the unchanged bound, and that an earlier release cannot prove a head
      whose plan exceeds the bound. (The unreleased section's entry under Fixed names the cited form
      `proof:execution-digest` for a plan too large to carry, the carried form within a third of the
      bound, the unchanged 1 MiB bound, and that an earlier release proves such a head itself and is
      refused by the same bound; Prettier and Vale pass on it.)
