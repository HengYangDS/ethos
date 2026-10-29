# Design

## Context

See [proposal.md](proposal.md). The accepted `dev` carries every change the entry describes:
`hook-governed-phases`, `shared-quality-obligations`, `re2js-advisory-override` and
`hosted-shared-obligations`, whose hosted runs pass on the landed head.

## Goals / Non-Goals

**Goals:**

- One release that carries every change accepted since `v0.2.0-alpha.18`.
- A changelog entry that names every user-visible product change since `v0.2.0-alpha.18` and no
  development infrastructure.

**Non-Goals:**

- New fixes. Each one has its own Change.
- Rebuilding the GitLab CI supply image. It binds `package-lock.json`, which changed after its last
  refresh, and lacks mise's Node; its owner rebuilds it from an accepted head.

## Decisions

- **Release notes cover the product only.** The note that CI preparation installs the declared
  Node through mise describes ETHOS's own CI tooling (`tools/ci/toolchain/native.py`), which no
  adopter consumes, so the entry omits it.
- **The re2js note names the replaced runtime.** The `[Unreleased]` note says that the installed
  `v0.2.0-alpha.18` runtime ships re2js 2.8.6; the entry states that this release replaces it.
- **Both peers publish in one pass.** `.ethos/release.toml` declares `gitlab` and `github`. The
  `dev` and `main` refs and the tag go to both; the hosted release runs on GitHub, its declared
  distribution peer. A peer that becomes unreachable during the pass is reported as pending rather
  than claimed.
- **Advisories are read on the exact head.** The release build's own audit runs on the exact head
  before tagging; a new fixable finding stops the tag.

## Risks / Trade-offs

- [The GitLab peer becomes unreachable mid-pass] → GitHub still completes; the GitLab refs are
  reported as pending and published later from the same accepted objects.
- [GitLab hosted jobs refuse the stale supply image] → The release does not wait for it; the supply
  owner rebuilds and rebinds it from an accepted head.
- [An advisory is published between proof and tag] → The pre-tag audit refuses the tag, and the fix
  lands in its own Change before the release is retried.
