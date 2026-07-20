## Why

The Python vulnerability gate exports the frozen dependency set from `uv.lock`,
but then lets `pip-audit` resolve it again.  That default path creates a
temporary environment and upgrades `pip`, `wheel`, and `setuptools`, adding an
unbounded package-bootstrap network dependency before the intended audit runs.

## What Changes

- Treat the `uv export` output as the complete, pinned audit input.
- Invoke `pip-audit` with `--no-deps --disable-pip` so it audits that input
  without dependency resolution or pip bootstrap.
- Preserve the existing local owner-gate evidence envelope and explicit
  non-claims for OSV, image/package scanning, hosted CI, and publication.
- Add a regression assertion that keeps both flags on the owner script.

## Capabilities

- `quality`: subject=python-vulnerability-audit; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=ci,script,test,evidence; facet:authority=source,test,openspec,claim,evidence

## Out Of Scope

- Activating OSV, image/package, or external-signing scanners.
- Changing the vulnerability service, dependency lock format, or remote
  publication policy.
- Claiming hosted CI success from this local owner gate.
