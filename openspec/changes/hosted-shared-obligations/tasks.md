# Tasks

## 1. Repairs

- [x] 1.1 Decide focused code selection by what the selected gates verify in
      `repository/policy/gates.py`. Done when a focused document gate implemented by a repository
      script compiles no code obligation in `test_gate_composition.py`, and
      `prove --host --execute --gate external-links` on the lane executes the gate.
      (At `0a1c79bd2` the composition cases passed and the focused hosted `external-links` ran and
      passed.)
- [x] 1.2 Give each `command_scope` ownership of the commands started under it in
      `adapters/process.py`. Done when a handled failure in a nested scope leaves a sibling's
      command running, an enclosing cancellation still ends a nested scope's command, and the
      process and capture suites pass.
      (The process, capture, lifecycle, worktree-effect and runner suites passed at `0a1c79bd2`.)
- [x] 1.3 Install the declared Node through mise in `tools/ci/toolchain/native.py`. Done when the
      supply cases show Node in the locked install and a missing Node failing an immutable image's
      preparation.
      (The Go, Node and hosted supply cases passed at `0a1c79bd2`.)

## 2. Contract Texts

- [x] 2.1 Add the focused-selection, nested-scope and clean-runner scenarios to the quality
      requirements. Done when strict validation passes and the simulated archive leaves every spec
      valid.
      (`openspec` passed at `0a1c79bd2`; the simulated archive validated every spec.)
- [x] 2.2 Record the repair under `[Unreleased]` in `CHANGELOG.md`. Done when `markdown-lint` and
      `prose` pass.
      (Both gates passed at `0a1c79bd2`.)

## 3. Acceptance

- [ ] 3.1 Repeat the hosted quality job's preparation and `hosted_verification` session on the lane
      head with a fresh mise data directory and tool cache. Done when every gate passes.
