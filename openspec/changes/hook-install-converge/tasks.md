# Tasks

## 1. Reproduce the loop

- [ ] 1.1 Add `test_an_install_never_names_itself_as_its_next_step` to
      `tests/unit/adapters/repo/hook/test_generation.py`, one case for a deferred reclamation and
      one for a refusal, in fixture repositories. Done when both fail at `23538df6b` on the
      `next.argv` assertion.
- [ ] 1.2 Point the four assertions that pin the old continuation at the new one, in
      `test_activation.py`, `test_generation.py` and `tests/unit/cli/test_hook_commands.py`. Done
      when each fails at `23538df6b` for its continuation alone.

## 2. End the loop

- [ ] 2.1 Stop hook activation writing `next_action` into its binding. Done when the two adapter
      tests of task 1.2 pass.
- [ ] 2.2 Continue a deferred or refused installation to `ethos status --root <root> --json`, and
      name the reset only to a request that is not that reset. Done when the tests of tasks 1.1 and
      1.2 pass.

## 3. Guard

- [ ] 3.1 Add the predicate and its table to `tests/unit/kernel/test_operation_catalog.py`. Done
      when eight cells fail at `23538df6b`, all 48 pass with task 2, and the module stays under 500
      effective lines.

## 4. Documents

- [ ] 4.1 Add the `command-plane` and `runtime-activation` deltas. Done when
      `openspec validate hook-install-converge --strict` passes.
- [ ] 4.2 State the continuation in `docs/reference/command-plane.md` and `rules/hooks.md`. Done
      when Prettier accepts both files.
- [ ] 4.3 Add the `Fixed` entry to `CHANGELOG.md` under `[Unreleased]`. Done when the entry names
      the old and the new continuation.

## 5. Lane, hosted and owner tasks

- [ ] 5.1 Owner: decide whether Breaking (4), the move of reclamation to `hook retire-supply`,
      joins this Change at its measured size or becomes its own Change. Done when the decision is
      recorded in the release-candidate plan's owner.
- [ ] 5.2 Lane: apply the patch under a passing `ethos lane prewrite` and commit it. Done when the
      lane head holds every path of the patch.
- [ ] 5.3 Lane: pass readiness and the full proof at the lane head. Done when both pass on the
      committed head, with product at most 45 and tests at most 180 line-equivalents above the lane
      base.
- [ ] 5.4 Lane: run the prose gate on the changed Markdown. Done when Vale and codespell report no
      finding.
