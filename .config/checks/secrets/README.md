# Secret scanning

The secret-scanning gate is [gitleaks](https://github.com/gitleaks/gitleaks).

The root policy is a current installed-hook binding, not a Gitleaks parser
restriction. The scanner already receives its path explicitly. Relocation must
update the ETHOS hook and scanner together: removing only the old file would
make the predecessor hook treat secret scanning as an absent capability.

- Policy: `/.gitleaks.toml` (`[extend] useDefault = true`)
- Supply identity: repository `.config/mise/config.toml` and `.config/mise/mise.lock` (selection and platform artifacts)
- Integrity: `tools/ci/toolchain/native.py` verifies locked archives and installed bytes; no system installation
- Runner: `tools/ci/scripts/run-secrets-scan.sh`
- Scope: the runner materializes `git ls-files` into a temporary
  `ethos-gitleaks-tracked` mirror before scanning, so the gate covers tracked
  source deterministically and excludes gitignored local caches or generated
  host-state residue.
