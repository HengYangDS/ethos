## Context

Official OpenSpec owns the active Change, quality delta, strict lifecycle
validation, and archive transition. ETHOS owns the tracked Git hook, reusable
quality runners, tool-version boundary, mutation admission, and local proof.

The current pre-commit hook already establishes the repository root, enumerates
the staged tracked paths, checks staged Python formatting, and invokes exact
write admission. The missing boundary is a fast index-only secret scan before
those ordinary checks. The full secret owner remains
`tools/ci/scripts/run-secrets-scan.sh`, which intentionally materializes the
tracked tree, writes quality evidence, and scans history; that behavior is too
large and stateful for commit-time admission.

## Design

### Repository-owned staged runner

Create `tools/ci/scripts/run-staged-secrets-scan.sh` as the only command body
for staged secret admission. It resolves or accepts the repository root,
requires a local `gitleaks` executable reporting version `8.30.1`, and executes:

```text
gitleaks git --staged --config <root>/.gitleaks.toml --redact=100 --no-banner <root>
```

The runner performs no bootstrap, download, installation, cache mutation,
report write, full-tree scan, or history scan. Missing and mismatched binaries
return stable diagnostic tokens that name the expected version but never print
environment contents or matched values.

### Hook ordering

After the hook proves the staged set is non-empty, it invokes the staged runner
before constructing the staged-Python set. A non-zero scanner result exits
immediately, so Ruff and `ethos.cli hook admit pre-tool` cannot run after a
finding or unavailable tool. A zero result preserves the current Ruff and
repository-root-bound admission path unchanged.

### Evidence boundary

Gitleaks owns detection and redaction; the wrapper does not parse or re-emit a
finding. Focused tests use a fake executable to prove version admission,
argument ordering, exit-code propagation, and downstream short-circuiting.
One local compatibility probe already established that gitleaks 8.30.1
`git --staged` rejects a synthetic secret while `--redact=100` keeps its value
out of stdout/stderr. That probe is diagnostic context, not final proof.

## Alternatives

- Inline the complete gitleaks command in `.githooks/pre-commit`: rejected
  because reusable command and version policy would be embedded in a projection.
- Reuse `run-secrets-scan.sh`: rejected because its bootstrap, installation,
  tracked-tree mirror, report files, and history scan violate the commit-time
  boundary.
- Use a hook framework or auto-install gitleaks: rejected because it adds a
  second hook authority and hidden network/host mutation.
- Replay `gitleaks protect --staged`: rejected because the command is absent
  from the pinned current CLI.

## Proof Strategy

1. Add failing tests for the runner contract and hook ordering before writing
   the runner or hook integration.
2. Implement the smallest runner and hook call that make those tests pass.
3. Run the focused hook tests, shell lint, config/docs checks, claim validation,
   strict OpenSpec lifecycle, and changed-path planning.
4. Commit the stable implementation, archive through official OpenSpec
   semantics, refresh parity if required, and obtain HEAD-bound executed proof
   before land and accepted-root closeout.

Rollback is a normal Git revert of the isolated runner/hook integration. A
missing local binary remains a blocking diagnostic; it must not be weakened to
recover a green commit path.
