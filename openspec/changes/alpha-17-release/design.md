# Design

## Context

See [proposal.md](proposal.md). The accepted `dev` carries every change the entry describes, and
both declared peers, GitLab and GitHub, are reachable.

## Goals / Non-Goals

**Goals:**

- One release that carries every accepted change, so each adopter rebinds once.
- A changelog entry that names every user-visible product change since `v0.2.0-alpha.16` and no
  development infrastructure.

**Non-Goals:**

- New fixes. Each one has its own Change.
- Rebuilding the GitLab CI supply image. It hashes the whole `package-lock.json`, which this
  release changes; its owner rebuilds it from this release's accepted head.

## Decisions

- **Release notes cover the product only.** The entry keeps the four knowledge notes under
  Changed, because the wheel ships the product design contract, the Docs Registry and the glossary
  (`pyproject.toml` force-include), and the decision index and the terminal plan are the governance
  those documents cite. The refreshed GitLab CI supply binding is development infrastructure that
  no adopter consumes, so the entry omits it.
- **Both peers publish in one pass.** `.ethos/release.toml` declares `gitlab` and `github`. The
  `dev` and `main` refs and the tag go to both; the hosted release runs on GitHub, its declared
  distribution peer. A peer that becomes unreachable during the pass is reported as pending rather
  than claimed.
- **No advisory changed since `v0.2.0-alpha.16`.** The npm, Python and native supply is unchanged,
  so the entry repeats no advisory. The release build's own audit runs on the exact head before
  tagging.

## Risks / Trade-offs

- [The GitLab peer becomes unreachable mid-pass] → GitHub still completes; the GitLab refs are
  reported as pending and published later from the same accepted objects.
- [GitLab hosted jobs refuse the supply image after this release] → The image's input manifest
  binds `package-lock.json`, so jobs fail their checksum until the supply is rebuilt for this
  release's head. The release does not wait for it; the supply owner rebuilds and rebinds it.
