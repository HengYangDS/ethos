# Proposal

## Why

ETHOS keeps optional local emulators of its hosted CI: `act` for GitHub and `gitlab-ci-local` for
GitLab, behind `tools/ci/ci_templates.py emulator-evidence`. They need Docker, a declared image per
provider and a standalone Git snapshot of the checkout, and their evidence is local by contract, so
it never stands in for a hosted run. No gate, proof or release step runs them; the release guide
lists them as optional, and the tooling lives only in ETHOS's own repository. The approved
end-state design deletes them (section 10, `ci-emulation-retirement`).

## What Changes

- Delete the local provider emulation: the `emulator-evidence` command and its helpers in
  `tools/ci/ci_templates.py`, the source snapshot in `tools/ci/provider_materialization.py`, the
  emulator declaration reader in `tools/ci/ci_projection.py`, the `emulator_*` and
  `forbidden_log_patterns` fields and the `[evidence]` table of
  `.config/checks/ci-projection/policy.toml`, and their tests.
- `tools/ci/ci_templates.py` keeps only `check-templates`, which the `ci_templates` gate and the
  format-selection policy use.
- The specifications, documents and repository model stop describing local emulation: the
  repository-governance scenario "Local provider emulation remains local evidence" now says that
  ETHOS never reads a hand-run emulator's output, and the quality requirements no longer name an
  emulation plane.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: provider projections no longer define local emulator evidence.
- `quality`: the evidence planes and hosted execution no longer name local emulation.

## Impact

`tools/ci/`, `.config/checks/ci-projection/policy.toml`, the CI projection tests, three documents,
the repository model and its generated diagram, and `CHANGELOG.md`. No product code, package
topology or adopter configuration changes.
