# Tasks

## 1. Deadline

- [ ] 1.1 Raise the npm seed deadline in `tools/ci/toolchain/npm.py` from 120 to 600 seconds. Done
      when the module bounds every npm command at 600 seconds and the supply contract tests in
      `tests/architecture/ci/test_supply_contract.py` pass.

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` to GitHub and GitLab. The landed head's hosted `windows-11-arm` leg must pass before the
  `0.2.0-alpha.21` tag.
