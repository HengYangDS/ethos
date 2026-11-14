# Design

## Context

See the [proposal](proposal.md) and the [quality delta](specs/quality/spec.md). ETHOS's pipelines
are one CUE model, `.config/ci/pipeline.cue`, from which `ethos lane project` generates
`.github/workflows/ci.yml` and `.gitlab-ci.yml`; ETHOS does not instantiate the shipped template.
This design applies decision 10 of the archived `common-base-plan` design, whose order (decision 12)
places this Change first among the release-candidate editors of the model. "Packet N" is an item of
`docs/research/foundations/hosted-ci.md`.

## Goals / Non-Goals

Goals:

- A `dev` push near 40 minutes on GitHub and under 15 on GitLab, within 10 percent, measured from a
  run's first attempt to its final conclusion with a capacity cancellation counted as a failure.
- One commit-range admission per event on each Forge.
- One required check whose name no supply, tool or runner change moves.
- No product line and no `tools/` line.

Non-Goals:

- A shorter test gate, which is rc's `gate-reuse`: the full-set job stays GitHub's critical path at
  about 38 minutes.
- The template and adopters, which are the design's Change 7. `.config/ci/verification.cue`,
  `.config/checks/ci-projection/policy.toml` and the supply `Dockerfile` do not change; the last two
  are hashed supply inputs, so this Change needs no supply image rebuild.
- Any forge setting; each is an owner task in this Change's workflow follow-up.

## Decisions

1. **Roles by event.** On GitLab two rule lists replace the single commit-scoped one. Conformance
   (`ethos:host-conformance`, `ethos:npm`) keeps today's rule behind a schedule rule. The full set
   (`ethos:verify`, `ethos:external-links`) runs for a schedule, a merge request, a batch head and a
   `main` that differs from `dev`. GitLab treats every merge request as its own, since it cannot
   know that GitHub verified the source.
2. **A batch head without typed inputs.** The projection renders each Forge file as one YAML
   document, so GitLab `spec:inputs` waits for Change 7. A `web` or `api` pipeline on a proposal ref
   carries the head in the pipeline variable `ETHOS_QUALIFY_HEAD`, and a workflow rule refuses the
   pipeline when that variable differs from its commit: a stale or undeclared head creates no
   pipeline instead of a green conformance-only one. On GitHub the `qualify_head` input is compared
   with the run's commit in the condition of every commit-scoped job and again in the aggregate.
3. **One table of conditions.** `perPushJobs` maps each per-push job to the condition it runs under;
   each job's `if` and the aggregate's expectation both read it. The aggregate requires `success`
   where the condition holds and `skipped` elsewhere, so a job that wrongly skips fails the check.
   Admission's condition is its event, a push or pull request: a dispatch or schedule pushes no
   range, so admission is expected skipped there. Rejected: passing any skipped job, under which a
   wrong `if` passes silently.
4. **Tiers inside the matrix.** Host conformance stays one job whose matrix `include` is chosen by
   expression from three leg lists: push, push with Windows, and full. A leg carries `platform`,
   `runner`, `python` and `timeout`, and the job is named by `platform` and `python`. Rejected: one
   job per tier, which renames checks by tier.
5. **Timeouts from one table.** `timeoutMinutes` holds the minutes of each job class, and
   `classGates` names the gates a class runs. `compiled.checks` holds one entry per class and gate,
   so a class whose minutes do not exceed a gate's `timeout_seconds` fails compilation and names
   both. The values are provisional: maxima of four or five observed runs, not a p99, with supply,
   release and publication unsurveyed and set generously. The full set takes 130 minutes because
   `unit-architecture` declares 7,200 seconds, although the job takes about 38 minutes on GitHub and
   up to 56 on GitLab.
6. **Cancellation.** The by-ref concurrency group covers pull requests as well as proposal pushes,
   and GitLab merge-request pipelines become interruptible on a new commit. Batch-head and scheduled
   runs are never cancelled.
7. **Caches and the lockfile.** Restore steps go into the verification jobs only and save steps only
   on the schedule event, which GitHub runs on the default branch `main`, whose caches every branch
   may read. The pinned `setup-uv` action's own cache is turned off in the same step, after its
   `action.yml` is read at the pinned commit. `actions.lock` is written by `gh actions-lock` and
   checked offline by one architecture test until Change 7 moves that check into
   `lane project --check`.
8. **Schedule.** One weekly cron in the model, Saturday 19:00 UTC, provisional until the owner
   confirms it. GitLab's schedule is a forge object on `dev`.

## Risks / Trade-offs

- The release legs' inventory step for macOS 3.14 and Windows moves from every push to batch heads;
  Linux x64 3.14 still runs per push.
- Windows, and macOS at 3.13 and 3.14, are qualified only at batch heads and weekly, so a defect
  there is found up to one batch late.
- `hosted checks` neither needs the external link job nor reads its result. That job observes
  sites the repository does not own, reports, and is allowed to fail on both providers, as before
  this Change, when the two aggregates needed only the quality gates. An earlier form of this
  design needed it and relied on what GitHub reports for a job that fails under its own
  `continue-on-error`, which GitHub's contexts reference does not state; on 2026-11-14 that job
  failed on `dev` for three redirecting links while both providers' runs succeeded.
- GitLab's batch-head trigger needs a role that may pass pipeline variables, against packet 10's
  recommendation, until Change 7 replaces it by typed inputs. Its half of the qualification stays a
  prose gate.
- 130 minutes exceeds the 60-minute job timeout observed on GitLab, so the runner's maximum timeout
  must allow it.
- A timeout set too low turns slowness into failure on the release candidate's critical path.

## Migration Plan

1. Land the Change. Owner pushes bypass the ruleset; pull requests stay pending until step 3.
2. Read `hosted checks` as reported for `dev`'s run.
3. The owner replaces the required checks by `hosted checks`, keeps the previous list to restore,
   and reads the ruleset back.
4. Rollback: revert the Change and restore the previous required checks.

## Open Questions

- Does the root layout admit `actions.lock` where `gh` writes it?
- Should `unit-architecture`'s 7,200-second timeout fall once the hosted duration is measured, so
  that the full-set class can follow its p99?
