# Tasks

## 1. Gate provider identity

- [ ] 1.1 Compare a gate's provider references by the provider each names. Done when
      `test_gate_executor_malformed_shapes_fail_closed` refuses an ID with its legacy name among
      the providers and among the verification providers, and
      `test_gate_names_distinct_providers_under_any_spelling` accepts two providers under
      different spellings and two names that the catalog lacks.
- [ ] 1.2 Hold a verification provider reference in the gate schema to the form and the unique
      items of a provider reference. Done when
      `test_gate_schema_holds_a_verifier_reference_as_the_model_does` passes and Prettier accepts
      the schema.

## 2. Gap registry

- [ ] 2.1 Return a copy of a row from the registry's two row readers. Done when
      `test_a_row_handed_to_a_reader_is_its_own_copy` passes.
- [ ] 2.2 Record the family-prefix measurement as the draft Change `gap-code-literals`. Done when
      its proposal states the measured counts, its owner, its next action and its review date,
      and `openspec validate gap-code-literals --strict` passes.

## 3. Documents

- [ ] 3.1 Add the changelog entry under Unreleased, Fixed. Done when Prettier and the prose gate
      accept `CHANGELOG.md`.

## 4. Acceptance

- [ ] 4.1 Pass the focused gates on the lane head: the test modules that import a changed module,
      the seven whole-repository guards, Ruff, ty, import-linter,
      `openspec validate gate-provider-identity --strict` and Prettier. Done when each reports no
      finding.
- [ ] 4.2 Measure the source budget against the lane base. Done when the measured figures are
      recorded beside the preparation's: product +6.4 and tests +51.8 line-equivalents.

## 5. Lane, hosted and owner tasks

- [ ] 5.1 Pass the precheck, readiness and one proof on the committed lane head. Done when each
      passes.
