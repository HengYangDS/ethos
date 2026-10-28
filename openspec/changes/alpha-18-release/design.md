# Design

## Context

See [proposal.md](proposal.md). The accepted `dev`, `59157bd0a`, carries every change the entry
describes. The route's next planned release follows `shared-quality-obligations`; this release
publishes the work accepted before it, because adopter operations wait for those fixes.

## Goals / Non-Goals

**Goals:**

- One release that carries every change accepted since `v0.2.0-alpha.17`.
- A changelog entry that names every user-visible product change since `v0.2.0-alpha.17` and no
  development infrastructure.

**Non-Goals:**

- New fixes. Each one has its own Change.
- The release that follows `shared-quality-obligations`, with the first application of the source
  budget ratchet. It stays as the route orders it.
- Rebuilding the GitLab CI supply image. It binds `pyproject.toml` and `package-lock.json`, which
  changed after its last refresh; its owner rebuilds it from an accepted head.

## Decisions

- **Release notes cover the product only.** Two notes describe ETHOS's own development
  infrastructure, which no adopter consumes: the names of its hosted conformance jobs
  (`.config/ci/pipeline.cue`, `.github/workflows/ci.yml`) and the hang limit of its own test
  configuration (`.config/checks/pytest/pytest.toml`). The entry omits both, as the `0.2.0-alpha.17`
  entry omitted the refreshed GitLab CI supply binding. The knowledge notes stay under Changed,
  because the wheel ships the product design contract that they change.
- **Both peers publish in one pass.** `.ethos/release.toml` declares `gitlab` and `github`. The
  `dev` and `main` refs and the tag go to both; the hosted release runs on GitHub, its declared
  distribution peer. A peer that becomes unreachable during the pass is reported as pending rather
  than claimed.
- **No advisory changed since `v0.2.0-alpha.17`.** `uv.lock`, `package-lock.json` dependencies and
  the native supply are unchanged, so the entry repeats no advisory. The release build's own audit
  runs on the exact head before tagging.

## Risks / Trade-offs

- [The GitLab peer becomes unreachable mid-pass] → GitHub still completes; the GitLab refs are
  reported as pending and published later from the same accepted objects.
- [GitLab hosted jobs refuse the stale supply image] → The release does not wait for it; the supply
  owner rebuilds and rebinds it from an accepted head.
- [A hosted Windows job fails while downloading Node] → The failed job is rerun once with unchanged
  inputs; the supply fix belongs to `bounded-supply-and-state`.
