# Tasks

## 1. Preview

- [x] 1.1 Report `adoption_exit_not_adopted` for a repository with no selector and no hooks path
      that ETHOS owns, and ask for a decision without a record only while such a path remains.
      Done when tests show a never-adopted and a hand-unbound repository refused as not adopted,
      and a repository whose user restored the hooks path planning only the selector removal.
      Evidence: the not-adopted and no-record tests in `test_exit.py`.
- [x] 1.2 Block the exit while a running process refers to the runtime or hooks generations, and
      list unlanded topic branches. Done when tests show a running process blocking the preview,
      and an unlanded branch listed while a landed one is not. Evidence: `test_exit.py`.

## 2. Apply

- [x] 2.1 Apply the exit under the selection lock in the fenced order, with a receipt before the
      first effect. Done when tests show the request refusals without effect, the recorded
      configuration restored, both selectors and the record removed, and the receipt's hashes.
      Evidence: the apply and request tests in `test_exit_apply.py`.
- [x] 2.2 Compensate a failed exit exactly, and keep worktree configuration enabled while a
      worktree needs it. Done when tests show a failure after the restoration leaving the prior
      state, and `extensions.worktreeConfig` kept for a worktree with its own configuration.
      Evidence: `test_exit_apply.py`; both tests fail against mutated code.
- [x] 2.3 Reclaim local generations inside the fence, and name each one kept as residue. Done when
      a test shows every checked generation either removed or named. Evidence: `test_exit_apply.py`.

## 3. Status and surfaces

- [x] 3.1 Report the exit in status from its receipt. Done when a test shows the exit fact after an
      apply and no exit fact before it. Evidence: the status test in `test_exit_apply.py`.
- [x] 3.2 Write the `runtime-activation` delta, and update the command reference, the CLI help and
      the MCP description. Done when strict validation and the cumulative archive simulation pass.
      Evidence: both pass after each commit.
