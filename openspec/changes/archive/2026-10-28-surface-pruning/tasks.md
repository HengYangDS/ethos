# Tasks

## 1. Prune

- [x] 1.1 Make `push_admission_report` name the exact accepted-closeout command for
      `accepted_closeout_effect_not_attested`, from the builder now in
      `adapters/mutation/remediation/guidance.py`. Done when the shared-command regression shows
      status, plan, closeout and the push report agreeing
      (`tests/unit/cli/test_contracts_closeout.py`) and `lint-imports` keeps the layer contract.
- [x] 1.2 Remove `ethos hook pre-push` and its option fields. Done when the retired-surface
      regression reports `Unknown command` (`tests/unit/cli/test_terminal_command_surface.py`) and
      the publication suites pass through the native producer (`tests/unit/cli/land/publication/`).
- [x] 1.3 Remove `measure.effective_code_lines`. Done when no product, test, tool or
      governed-repository reference remains.

## 2. Record

- [x] 2.1 Record the removal under `[Unreleased]` in `CHANGELOG.md`. Done when `markdown-lint` and
      `prose` pass.

## Workflow follow-up

- Archive this Change with its lane code, prove the archived head once, land it, close out and
  publish `dev` to both peers.
- Tell the `reference-observation-repair` lane when this lands, so that it rebases onto the freed
  headroom.
