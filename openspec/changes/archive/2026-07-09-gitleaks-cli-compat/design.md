# Design

## Principle

Provider tools remain adapters. ETHOS owns the quality boundary and evidence;
gitleaks owns its command-line shape. When the adapter's native CLI changes, the
owner script must adapt without weakening the gate.

## Minimal Mechanism

- Preserve the tracked-file mirror scan for current source cleanliness.
- Preserve the separate Git history scan.
- Replace `gitleaks git --source "${repo_root}"` with `gitleaks git ...
  "${repo_root}"`, matching gitleaks 8.30.1 help output.
- Keep reports under `build/evidence/quality/secrets/`.

## Kernel Binding

```text
Subject = secret-scanning quality gate
Commitment = gitleaks owner script, root policy, tool catalog, quality spec
Change = history-scan invocation compatibility
Evidence = local script run, architecture tests, shell lint, OpenSpec lifecycle
Claim = digest-bound evidence record
Chronicle = this archived carrier and dated evidence
```

## Alternatives

- Drop history scanning: rejected because it weakens release supply-chain proof.
- Pin an older gitleaks CLI: rejected because the configured installer already
  targets 8.30.1 and local developers may have that version.
- Inline scanner logic in CI: rejected because owner scripts remain the SSOT.
