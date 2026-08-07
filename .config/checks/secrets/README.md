# Secret scanning

The secret-scanning gate is [gitleaks](https://github.com/gitleaks/gitleaks).

Its policy lives in the repository-root `.gitleaks.toml` because gitleaks
resolves its configuration from a git-discoverable location, not from a nested
concern directory. This folder records the ownership boundary so the concern is
discoverable alongside the other `.config/checks/<concern>/` gates.

- Policy: `/.gitleaks.toml` (`[extend] useDefault = true`)
- Installer: `tools/ci/scripts/install-gitleaks.sh` (pinned prebuilt binary)
- Runner: `tools/ci/scripts/run-secrets-scan.sh`
- Scope: the runner materializes `git ls-files` into a temporary
  `ethos-gitleaks-tracked` mirror before scanning, so the gate covers tracked
  source deterministically and excludes gitignored local caches or generated
  host-state residue.
