# Design

## Context

See [proposal.md](proposal.md). Since `v0.2.0-alpha.20` the accepted `dev` has landed
`reference-grammar-owners`, `windows-arm64-delivery` and `release-path-repairs`. The last removed
the npm workspace from the locks, so the supply image built from its landed head stays valid for
every later version bump.

## Goals / Non-Goals

**Goals:**

- One release that carries every change accepted since `v0.2.0-alpha.20`.
- A changelog entry that names every user-visible product change since `v0.2.0-alpha.20`, the known
  advisories in the release's shipped bytes, and no development infrastructure.
- GitLab verifies the release head with a bound supply image whose inputs match it.

**Non-Goals:**

- New fixes. Each one has its own Change, including the follow-ups that the three Changes defer.
- Qualifying `windows-arm64` beyond the release's own leg and DDWG's consumer acceptance.

## Decisions

- **Release notes cover the product only.** ETHOS's own CI supply binding is development
  infrastructure that no adopter consumes, so the entry omits it.
- **The supply image is bound in this Change.** It was built by the `supply_image` dispatch on
  `dev` at the `release-path-repairs` head; none of its inputs changes here, so the image matches
  the release checkout. A separate binding Change, as for `0.2.0-alpha.19`, is no longer needed.
- **Shipped advisories are named again.** The wheels and installed runtimes ship the same uv and npm
  as `v0.2.0-alpha.20`, so the entry restates their known advisories as the release build's audit
  reports them on the landed head.
- **Both peers publish in one pass.** `.ethos/release.toml` declares `gitlab` and `github`. The
  `dev` and `main` refs and the tag go to both; the hosted release runs on GitHub, its declared
  distribution peer. A peer that becomes unreachable during the pass is reported as pending rather
  than claimed.
- **Advisories are read on the exact head.** The release build's own audit runs before this
  Change's proof and again on the exact release head before tagging; a new fixable finding stops the
  tag.

## Risks / Trade-offs

- [The GitLab CI guest's disk was exhausted on 10-29] → A job that fails with `ENOSPC` is an
  environment failure, not a verdict on the head; the guest needs the maintenance window the user
  grants. GitHub, the declared distribution peer, still verifies the head.
- [GitHub's hosted macOS arm64 capacity cancels a job before a runner acquires it] → The cancelled
  jobs are rerun; a cancellation without an acquired runner is not a verdict on the head.
- [The emulated `windows-arm64` release leg fails] → Windows legs are optional, so the release
  omits `windows-arm64` explicitly and DDWG's Windows job stays red until a repair is released.
- [An advisory is published between proof and tag] → The pre-tag audit refuses the tag, and the fix
  lands in its own Change before the release is retried.
