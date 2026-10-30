# Design

## Context

See [proposal.md](proposal.md). Since `v0.2.0-alpha.21` the accepted `dev` has landed
`hosted-flake-repairs`, `per-file-ceiling-parameters`, `retire-unreachable-product-code`,
`deleted-input-dependency`, `documents-within-ceiling` and `installed-operational-roots`. Three of
them have no product effect: `retire-unreachable-product-code` removes code that no live path runs,
`documents-within-ceiling` moves documentation within the new ceiling, and
`installed-operational-roots` installs the moved reference so that the installed text is unchanged.
The bound GitLab supply image hashes eight inputs, and no landed Change edits any of them.

## Goals / Non-Goals

**Goals:**

- One release that carries every change accepted since `v0.2.0-alpha.21`.
- A changelog entry that names every user-visible product change since `v0.2.0-alpha.21`, the known
  advisories in the release's shipped bytes, and no development infrastructure.
- GitLab verifies the release head with the bound supply image, whose inputs match it.

**Non-Goals:**

- New fixes. Each one has its own Change, including the follow-up for the two specified functions
  that no live path runs, `release_policy_report` and `materialize_explicit_release`.
- Moving the governed repositories within the new ceilings. Each owner does that when rebinding to
  this release.

## Decisions

- **Release notes cover the product only.** Test repairs, removed unreachable code and moved
  documentation change no adopter's behavior, so the entry omits them.
- **The supply image is not rebound.** Its inputs are `uv.lock`, `package-lock.json`, the Mise
  configuration and lock, the ci-projection policy, the Dockerfile with its ignore file, and the
  quality sample's lock. None changed since `c36790cd8`, the head that built it.
- **Shipped advisories are named again.** The wheels and installed runtimes ship the same uv and npm
  as `v0.2.0-alpha.21`, so the entry restates their known advisories as the release build's audit
  reports them on the landed head.
- **Both peers publish in one pass.** `.ethos/release.toml` declares `gitlab` and `github`. The
  `dev` and `main` refs and the tag go to both; the hosted release runs on GitHub, its declared
  distribution peer. A peer that becomes unreachable during the pass is reported as pending rather
  than claimed.
- **Advisories are read on the exact head.** The release build's own audit runs before this
  Change's proof and again on the exact release head before tagging; a new fixable finding stops the
  tag.

## Risks / Trade-offs

- [The new ceilings block a governed repository at its next proof] → Only adopters that rebind to
  this release are affected. Each owner received the exact list of files above 500 on 2026-10-31,
  and a repository may declare a higher whole-tree value with its reason.
- [GitHub's hosted macOS arm64 capacity cancels a job before a runner acquires it] → The cancelled
  jobs are rerun; a cancellation without an acquired runner is not a verdict on the head.
- [The emulated `windows-arm64` release leg fails] → Windows legs are optional, so the release
  omits `windows-arm64` explicitly and DDWG's Windows job stays red until a repair is released.
- [An advisory is published between proof and tag] → The pre-tag audit refuses the tag, and the fix
  lands in its own Change before the release is retried.
