# Proposal

## Why

GHSA-gg6h-894w-4m9c (CVE-2026-116795, high), published on 2026-10-28, reports that re2js from
2.2.0 and before 2.8.7 matches lookbehind assertions in quadratic time. markdownlint 0.42.0
pins re2js 2.8.6 exactly, and markdownlint-cli2 0.24.0 pins markdownlint 0.42.0. Both are their
latest releases, so the product npm lock holds re2js 2.8.6 as a production dependency, and the
installed `v0.2.0-alpha.18` runtime ships it in the Node supply that the markdown lint gate runs. Upstream's bump of the pin to 2.8.8 is an open pull request
([DavidAnson/markdownlint#2338](https://github.com/DavidAnson/markdownlint/pull/2338)).

OSV already reports the advisory for the lock. The npm audit endpoint that the dependency gate reads
did not report it yet on 2026-10-29. When it does, the gate blocks every proof, because re2js has
releases that fix it.

## What Changes

- `package.json` overrides markdownlint-cli2's re2js with 2.8.8, beside the existing
  `markdown-it` and `smol-toml` overrides, and the product lock is re-resolved so that it holds one
  production re2js 2.8.8.
- `[Unreleased]` gains a Security note.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This changes the locked supply; `skip_specs: true` applies.

## Impact

`package.json`, `package-lock.json` and `CHANGELOG.md` change. The markdown lint gate runs
markdownlint 0.42.0 with re2js 2.8.8. The Linux supply image takes both npm files as inputs, so its
owner rebuilds and rebinds it from an accepted head.
