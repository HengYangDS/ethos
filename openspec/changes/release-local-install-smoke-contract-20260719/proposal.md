# Govern the Local Installation Smoke Owner

## Why

The release topology currently declares
`tools/ci/scripts/run-local-install-smoke.sh` as the local installation owner,
but the tracked executable does not exist. `ethos quality release-policy`
still reports ready because it validates remote topology and release metadata
without validating the declared local command surfaces. Local CI and full proof
also omit the installation check. This is a phantom owner and a false-ready
release boundary.

## What Changes

- Make release policy fail closed when a declared local verification or
  installation command is missing, escapes the repository, is not a regular
  file, or is not executable.
- Add one reusable `run-local-install-smoke.sh` owner that builds the workspace
  wheels, creates a fresh virtual environment, installs offline, verifies both
  package origins, and exercises installed CLI help and version surfaces.
- Bind the smoke evidence to a stable Git HEAD without claiming hosted CI,
  remote publication, or registry delivery.
- Invoke the same owner from local CI and the trust-bearing product full-proof
  graph, and register it in the gate and tool catalogs.

## Capabilities

- `repository-governance`: subject=release-local-install-owner-admission; reuse=extend; change=modify; facet:lifecycle=validation,release; facet:surface=cli,ci,script,test,docs,openspec,evidence; facet:authority=source,test,system,docs,openspec,claim,evidence
- `quality`: subject=fresh-offline-local-install-smoke; reuse=extend; change=add; facet:lifecycle=validation,release; facet:surface=ci,script,package,test,openspec,evidence; facet:authority=source,test,system,openspec,claim,evidence

## Impact

- Release-policy source and focused regressions.
- One reusable install-smoke owner, local-CI composition, and full-proof gate.
- Gate/tool declarations, release governance, claim, Chronicle, and parity
  evidence.

## Out Of Scope

- No second release configuration owner and no restored verbose
  `[publication.local]` block.
- No wholesale replay or cherry-pick of historical implementation commits.
- No rewrite of historical claims, Chronicles, or archived changes.
- No remote publication, hosted-CI success, registry publication, tag, or
  public-distribution claim.
- No change to the Node/npm compatibility contract.
