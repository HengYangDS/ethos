# Tasks

## 1. Packaging

- [ ] 1.1 Ship `docs/reference/operational-roots.md` with the command plane: add it to the wheel's
      `force-include` and the sdist's `only-include` in `pyproject.toml`. Done when
      `test_installed_navigation_preserves_required_links_without_source_checkout` passes.

## 2. Verification

- [ ] 2.1 Run the unit and architecture tests that the blocked proof did not reach. Done when they
      pass with the fix.

## Workflow follow-up

- Archive this Change and prove the archived head once.
