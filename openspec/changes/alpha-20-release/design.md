# Design

## Context

See [proposal.md](proposal.md). The accepted `dev` carries every change the entry describes:
`reference-owner-semantics`. The other Change since `v0.2.0-alpha.19`, `ci-supply-alpha-19`, binds
ETHOS's own GitLab CI supply image and changes no shipped byte.

## Goals / Non-Goals

**Goals:**

- One release that carries every change accepted since `v0.2.0-alpha.19`.
- A changelog entry that names every user-visible product change since `v0.2.0-alpha.19`, the known
  advisories in the release's shipped bytes, and no development infrastructure.

**Non-Goals:**

- New fixes. Each one has its own Change, including the follow-ups that `reference-owner-semantics`
  defers.
- Repairing ETHOS's GitLab CI guest. Its owner decides when a maintenance window opens.

## Decisions

- **Release notes cover the product only.** The supply binding of `ci-supply-alpha-19` describes
  ETHOS's own CI, which no adopter consumes, so the entry omits it.
- **Shipped advisories are named again.** The wheels and installed runtimes ship the same uv and npm
  as `v0.2.0-alpha.19`, so the entry restates their known advisories as the release build's audit
  reports them on the landed head.
- **Both peers publish in one pass.** `.ethos/release.toml` declares `gitlab` and `github`. The
  `dev` and `main` refs and the tag go to both; the hosted release runs on GitHub, its declared
  distribution peer. A peer that becomes unreachable during the pass is reported as pending rather
  than claimed.
- **Advisories are read on the exact head.** The release build's own audit runs before this
  Change's proof and again on the exact release head before tagging; a new fixable finding stops the
  tag.

## Risks / Trade-offs

- [GitLab's hosted jobs keep failing on the CI guest's disk and network] → The release does not
  wait for them. GitHub, the declared distribution peer, verifies the head, and the guest's owner
  decides its repair.
- [An advisory is published between proof and tag] → The pre-tag audit refuses the tag, and the fix
  lands in its own Change before the release is retried.
- [The GitLab peer becomes unreachable mid-pass] → GitHub still completes; the GitLab refs are
  reported as pending and published later from the same accepted objects.
