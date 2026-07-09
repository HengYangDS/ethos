# Gitleaks CLI Compatibility

## Why

Local CI reached the secrets gate and failed because gitleaks 8.30.1 no longer
accepts `gitleaks git --source <repo>`. The gate must follow the tool's native
shape instead of freezing an obsolete provider invocation.

## What Changes

- Keep the current tracked-tree scan as `gitleaks detect --source <tracked-mirror>
  --no-git`.
- Change the history scan to invoke `gitleaks git <repo>` with the repository as
  the positional argument.
- Add architecture-test coverage so the removed `--source` flag does not return
  to the history scan.

## Capabilities

- `quality`: subject=gitleaks-cli-compat; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=ci,script,test,openspec; facet:authority=tool-native-cli,source,test,openspec

## Out Of Scope

- No secret-policy relaxation.
- No claim that hosted CI passed.
- No replacement of gitleaks with another scanner.
