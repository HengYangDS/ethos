# Tasks

## 1. Retire local provider emulation

- [x] 1.1 Delete the `emulator-evidence` command and its helpers,
      `tools/ci/provider_materialization.py`, the emulator declaration reader, the policy's
      emulator fields and `[evidence]` table, and `tests/architecture/test_ci_emulator_runtime.py`,
      keeping `check-templates`. Done when the
      `ci_templates` and `github-workflow-syntax` gates and the CI projection tests pass, and the
      removed tooling lines are measured.
      (Effective lines: tools 1,303 to 731, minus 572; tests minus 107; the 249 CI projection,
      workflow, Nox, reference and entrypoint cases pass; `ci_templates` and
      `github-workflow-syntax` pass.)
- [x] 1.2 Remove local emulation from the specifications, `docs/architecture/gate-runner.md`,
      `docs/reference/configuration.md`, `docs/guides/release-and-publication.md` and the
      repository model with its generated diagram. Done when strict OpenSpec validation,
      `markdown_lint` and `prose` pass and `ethos lane project --check` conforms.
      (`openspec validate --strict` valid; `markdown_lint`, `prose` and `architecture_projection`
      pass; `lane project` regenerated the repository diagram.)
- [x] 1.3 Record the removal under Unreleased in `CHANGELOG.md`. Done when the docs gates pass.
      (The docs gates above pass.)

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
