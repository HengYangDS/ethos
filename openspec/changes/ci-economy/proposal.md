# Proposal

## Why

Hosted CI is the slowest step of every landing and of every release-candidate qualification. Over 30
`dev` pushes from 2026-11-07 to 2026-11-12 a GitHub run took 68.9 minutes at the median and a GitLab
pipeline 40.1; the `dev` run of 2026-11-13 took 71 minutes, and one GitLab pipeline timed out at 60
minutes under host load. The time goes to four Windows legs per push, one of them emulated, although
the release target declares no Windows journey, and to a full gate set that both Forges run on the
same commit.

The approved common-base design (`common-base-plan`) rules in its decision 10 that hosted CI proves
what the local proof cannot, once per plane. This Change is that design's Change 1 (decision 12),
the first of the release-candidate editors of `.config/ci/pipeline.cue`. Its targets are about 40
minutes on GitHub and under 15 on GitLab per `dev` push, within 10 percent.

## What Changes

- A ref published to both Forges gets its full gate set once, on GitHub. GitLab runs commit-range
  admission and conformance for it and keeps the full set for a merge request, a `main` that differs
  from `dev`, a batch head and the drift schedule.
- A push or pull request runs host conformance on Linux x64 at every supported Python version and on
  macOS arm64 at the lowest. A typed dispatch input adds the Windows legs; the full matrix runs for
  a batch head named by `qualify_head` and for a weekly drift schedule.
- Every push and pull request admits its commit range once, in `commit-policy`.
- **BREAKING** for the forge ruleset: one aggregate check, `hosted checks`, replaces
  `repository proof` and `package artifacts`, and host conformance jobs are named by platform id
  instead of runner label. The owner switches the required checks; no Change edits a forge setting.
- Every hosted job declares a timeout from one table, above the longest timeout of the gates it
  runs. No checkout persists its credentials. A newer push to a pull or merge request cancels its
  earlier run.
- GitHub's verification jobs restore lock-keyed download caches that only the scheduled run of
  `main` writes, and `actions.lock` records the workflow's action pins.
- The release guide requires the batch-head qualification on both Forges before `land --release`.

Out of scope: the shipped CI template (the design's Change 7), GitLab `spec:inputs`, the split of
the test gate (rc's `gate-reuse`), release queueing (`release-provenance`), runner isolation and
every forge setting.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: MODIFIED requirements `Each Forge verifies a published commit once`,
  `Hosted test feedback is visible and source bound`, `Hosted check names are stable identities` and
  `A newer proposal push supersedes its earlier run`; ADDED requirements
  `Hosted host conformance runs in declared tiers`, `One aggregate check reports the per-push jobs`,
  `Hosted jobs bound their time and credentials` and `Hosted download caches have one writer`.

## Impact

`.config/ci/pipeline.cue` and its two generated Forge files, `actions.lock`, the architecture tests
of the CI projections, `docs/guides/release-and-publication.md` and `openspec/specs/quality/spec.md`
through this Change's delta. No product line and no `tools/` line changes. After this Change rc's A9
item 8 and A11 read admission plus conformance from GitLab.
