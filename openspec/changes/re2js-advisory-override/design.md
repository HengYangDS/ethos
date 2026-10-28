# Design

## Context

See [proposal.md](proposal.md). The `markdownlint-cli2` scope of `overrides` in `package.json`
already replaces two exact pins in that dependency tree: `markdown-it` 15.0.3, for
GHSA-r7fv-28h4-cvq7, and `smol-toml` 1.9.1. markdownlint 0.42.0 is the only package in the lock that
depends on re2js. It imports only `RE2JS` and the `re` template tag, in `lib/markdownlint.mjs` and
the MD011, MD013 and MD039 rules.

## Goals / Non-Goals

**Goals:**

- The product lock holds no re2js version that the advisory affects.
- The markdown lint gate keeps its findings.

**Non-Goals:**

- Upgrading markdownlint or markdownlint-cli2. Their latest releases keep the 2.8.6 pin.
- A release. The next release carries the override, and its Security note names the version that
  `v0.2.0-alpha.18` ships.
- Changing the dependency gate or its policy.

## Decisions

- **re2js 2.8.8, the latest 2.8 release.** It fixes the advisory, it is the version that upstream's
  open bump proposes, and it stays on the line that markdownlint 0.42.0 was released with. re2js
  2.9.1 is newer, but no markdownlint release or pull request uses the 2.9 line yet.
- **The override is scoped to markdownlint-cli2,** like the two existing ones. Nothing else in the
  lock depends on re2js.
- **The override has an exit condition.** When a markdownlint-cli2 release depends on a markdownlint
  that requires re2js 2.8.7 or later, the supply refresh that adopts it removes the override.

## Risks / Trade-offs

- [re2js 2.8.8 changes markdownlint's findings] → The markdown lint gate runs over every authored
  Markdown file in the proof, so a changed finding fails it before landing.
- [re2js 2.8.8 declares `node >= 20` where 2.8.6 declared `node >= 18`] → ETHOS locks Node 26.12.1,
  and the Node supply that it ships is that runtime.
- [The npm audit endpoint reports the advisory before this lands] → Proofs of other Changes block on
  the dependency gate until this lands, so this Change lands before them.
- [Repositories run `v0.2.0-alpha.18`, which ships re2js 2.8.6] → markdownlint evaluates its own
  patterns over a repository's own Markdown. The next release carries the fix.
