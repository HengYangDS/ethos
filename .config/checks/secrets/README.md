# Secret scanning

The secret-scanning gate is [gitleaks](https://github.com/gitleaks/gitleaks).

[The native policy](gitleaks.toml) owns custom rules and extension of Gitleaks
defaults. The root `.gitleaks.toml` contains only a native `extend.path`
reference. It preserves bare-tool discovery and the installed ETHOS hook
entrypoint without copying rules or introducing a runtime configuration layer.
Both hook and CI execute from the repository root, which anchors the relative
reference. Missing or malformed referenced policy is an execution failure.

- Policy: `.config/checks/secrets/gitleaks.toml`
- Discovery: `.gitleaks.toml` (reference only)
- Supply identity: repository `.config/mise/config.toml` and `.config/mise/mise.lock` (selection and platform artifacts)
- Integrity: `tools/ci/toolchain/native.py` verifies locked archives and installed bytes; no system installation
- Runner: `tools/ci/scripts/run-secrets-scan.sh`
- Scope: the runner materializes `git ls-files` into a temporary
  `ethos-gitleaks-tracked` mirror before scanning, so the gate covers tracked
  source deterministically and excludes gitignored local caches or generated
  host-state residue.
