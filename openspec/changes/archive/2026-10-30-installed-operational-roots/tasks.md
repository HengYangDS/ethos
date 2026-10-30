# Tasks

## 1. Packaging

- [x] 1.1 Ship `docs/reference/operational-roots.md` with the command plane: add it to the wheel's
      `force-include` and the sdist's `only-include` in `pyproject.toml`. Done when
      `test_installed_navigation_preserves_required_links_without_source_checkout` passes.
      (With the fix on `2b7ff8d87` it passed, with `test_version_identity.py`, which builds the
      wheel and the sdist, and `test_product_design_contract.py`: 66 passed.)

## 2. Verification

- [x] 2.1 Run the unit and architecture tests that the blocked proof did not reach. Done when they
      pass with the fix.
      (Of the 7,737 collected tests the proof ran 4,016. On `606ad77da` the other 3,721 gave 3,718
      passed and 3 skipped; the navigation test, the only failure, passes with the fix, which
      changes no code.)

## Workflow follow-up

- Archive this Change and prove the archived head once.
