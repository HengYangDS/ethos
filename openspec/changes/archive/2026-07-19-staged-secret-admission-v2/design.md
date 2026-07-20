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

Gitleaks 8.30.1 does still accept the unadvertised compatibility command
`protect --staged`, despite omitting it from the advertised top-level command
list. Its current public `git` command explicitly documents `--staged`. A
scratch repository probe confirmed that both interfaces rejected the same
synthetic staged finding with full redaction. This Change selects
`git --staged` because it is the advertised current interface, not because the
legacy command is absent.

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
argument ordering, and exit-code propagation. Hook-level behavioral tests run
the tracked hook against fake scanner and downstream commands to prove that a
scanner failure prevents Ruff/admission and a clean result preserves the
existing continuation path. One local compatibility probe established that
gitleaks 8.30.1 `git --staged` and unadvertised `protect --staged` both reject a
synthetic secret while `--redact=100` keeps its value out of stdout/stderr.
That probe is diagnostic context, not final proof.

## Alternatives

- Inline the complete gitleaks command in `.githooks/pre-commit`: rejected
  because reusable command and version policy would be embedded in a projection.
- Reuse `run-secrets-scan.sh`: rejected because its bootstrap, installation,
  tracked-tree mirror, report files, and history scan violate the commit-time
  boundary.
- Use a hook framework or auto-install gitleaks: rejected because it adds a
  second hook authority and hidden network/host mutation.
- Replay inline `gitleaks protect --staged`: rejected because it is an
  unadvertised compatibility command, while `git --staged` is the advertised
  current interface; replay would also retain inline policy and weak behavioral
  proof.

## Proof Strategy

1. Add failing tests for the runner contract and hook ordering before writing
   the runner or hook integration.
2. Include executable hook failure and clean-continuation tests, not only static
   ordering assertions.
3. Implement the smallest runner and hook call that make those tests pass.
4. Run the focused hook tests, shell lint, claim validation, strict OpenSpec
   lifecycle, and changed-path planning.
5. Commit the stable implementation, archive through official OpenSpec
   semantics, refresh parity if required, and obtain HEAD-bound executed proof
   before land and accepted-root closeout.

Rollback is a normal Git revert of the isolated runner/hook integration. A
missing local binary remains a blocking diagnostic; it must not be weakened to
recover a green commit path.
