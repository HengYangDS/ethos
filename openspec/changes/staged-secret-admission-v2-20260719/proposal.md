## Why

ETHOS scans the tracked tree and Git history during full local/hosted quality
proof, but the tracked pre-commit hook does not inspect the staged index before
creating local history. The historical staged-secret lane attempted to close
that gap with `gitleaks protect --staged`; gitleaks 8.30.1 no longer provides
the `protect` command, so replaying that branch would install an obsolete and
untested commit boundary.

## What Changes

- Add one repository-owned staged-secret runner that requires the current
  pinned gitleaks version and invokes `gitleaks git --staged` with the checked-in
  policy and full redaction.
- Invoke that runner after confirming the index is non-empty and before Ruff or
  `ethos.cli hook admit pre-tool`.
- Fail closed with stable, non-secret diagnostics when gitleaks is missing or
  version-incompatible; never install tools or access the network from the
  commit hook.
- Add focused static and behavioral regressions for ordering, command shape,
  missing/version-mismatched tools, blocked findings, and the clean continuation
  path.

## Capabilities

### Modified Capabilities

- `quality`: subject=staged-secret-admission-v2; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=cli,test,ci,openspec; facet:authority=source,test,openspec

## Impact

- `.githooks/pre-commit`
- `tools/ci/scripts/run-staged-secrets-scan.sh`
- `.config/checks/secrets/README.md`
- focused hook tests, OpenSpec delta, claim, and Chronicle

## Out Of Scope

- Full tracked-tree or Git-history scanning, release evidence, or hosted-CI
  success claims.
- Automatic gitleaks installation, network access, host package-manager
  mutation, or workstation-only credential tooling.
- Changes to `.gitleaks.toml`, the release secret gate, provider workflows,
  remote publication, or the historical source Work Lane.
