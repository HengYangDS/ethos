# Design

## Context

See [proposal.md](proposal.md). The design record is
`build/runtime/work/hardening/post-beta6-hardening-draft.md`, section 1, as amended by its decision
of 09:5x. A read on this volume leaves an access time unchanged once it is newer than the
modification time, so using the environment never protects it. A gate's deadline is at most 7,200
seconds, far below the cleaner's three days, so one renewal covers an attempt.

## Goals / Non-Goals

Goals:

- No file of a running attempt's environment is old by access time.
- No scan or fixture copy depends on its source's last use.

Non-goals:

- Moving the scratch out of `$TMPDIR`. One test needs a temporary directory outside any repository
  (`tests/unit/lanes/status/test_projection.py`), and a killed attempt there needs no new reclaimer.
- Changing uv's link mode.

## Decisions

- **Sync, renew, run.** The probe runs `uv sync --locked --offline` with its environment, removed
  variables and deadline. A failed sync returns `unproven("behavior", "test_environment_sync_failed")`
  with that command's native fields. The probe then renews access times and runs
  `uv run --no-sync --offline` with the pytest arguments it used before. `--no-sync` implies
  `--frozen`, so the run carries no `--locked`.
- **The walk stays inside the scratch.** `os.walk` runs without following directory symlinks.
  The walk skips each symlink and calls `os.utime(path, ns=(now, st_mtime_ns))` on each directory
  and regular file.
- **Fresh copies.** `shutil.copy` replaces `copy2` in the gitleaks mirror and in the fixture
  copies of `tests/conftest.py` and `tests/support/runtime_scenarios.py`.

## Risks / Trade-offs

- The cleaner's access-time rule is inferred from a census of the 03:35 run, not read from its
  source. The regression proves the renewal itself, not the cleaner's behavior.
- A lane runs its pinned runtime's gate, so until a release carries this, a proof that spans 03:35
  stays exposed. A deleted source makes the gate block, never pass.
