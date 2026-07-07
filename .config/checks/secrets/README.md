# Secret scanning

The secret-scanning gate is [gitleaks](https://github.com/gitleaks/gitleaks).

Its policy lives in the repository-root `.gitleaks.toml` because gitleaks
resolves its configuration from a git-discoverable location, not from a nested
concern directory. This folder records the ownership boundary so the concern is
discoverable alongside the other `.config/checks/<concern>/` gates.

- Policy: `/.gitleaks.toml` (`[extend] useDefault = true` + allowlist)
- Installer: `.config/ci/scripts/install-gitleaks.sh` (pinned prebuilt binary)
- Runner: `.config/ci/scripts/run-secrets-scan.sh`
