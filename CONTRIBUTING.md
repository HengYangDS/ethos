# Contributing

ETHOS accepts changes through the `ethos ...` command plane and signed Git
history.

## Identity

Use your own organization-approved Git identity. ETHOS does not require a
single built-in author or a tracked identity allowlist. Git author and committer,
the Work Lane actor, the trusted signing principal, transport credentials, and
forge verification are separate facts. Configure your local identity and signer
through Git; the repository paradigm requires an SSH signature on every commit,
and a tracked `[commit_policy]` only restricts commit scopes and identities.

```bash
git config user.name "<your-name-or-team>"
git config user.email "<your-approved-email>"
git config commit.gpgsign true
git config gpg.format ssh
```

SSH signing is required for every commit in a governed repository. ETHOS verifies
the resulting Git object against the configured external trust anchor; it does
not turn author metadata into mutation authority.

## Commit Messages

Use this repository's [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
convention. The shared repository paradigm owns the accepted subject syntax;
see [commit integrity](docs/reference/command-plane.md#commit-integrity-and-accepted-history-repair):

```text
<type>: <description>
<type>(<scope>): <description>
```

- `type` identifies the kind of change: `feat`, `fix`, `docs`, `test`,
  `refactor`, `perf`, `build`, `ci`, `chore` or `revert`.
- `scope` is optional. When present, keep the literal parentheses and name the
  affected semantic area, such as `proof`, `lanes` or `cli`. The current policy
  accepts lowercase ASCII letters and digits, with single hyphens between
  nonempty segments.
- `description` is a nonempty summary after the colon and space.

```text
feat(proof): add evidence gate runner
fix(lanes): reject stale integration requests
docs(cli): clarify fast verification
ci: add GitLab verification pipeline
```

For an incompatible change, add `!` immediately before the colon, a
`BREAKING CHANGE: ...` footer, or both. Explain the incompatibility and migration;
for example, `feat(cli)!: replace the command contract`. Commit syntax alone
does not establish SemVer or release
compliance; [release governance](docs/governance/release-governance.md#semantic-versioning-and-changelog)
owns those obligations.

Avoid vague subjects such as `Update files` or product claims without evidence.

## Verification

Use scoped checks while editing and the standard proof at acceptance. A small
change does not need a full proof after every edit. Choose the path by its
effect and affected consumers, not only its line count.

| Path                 | Use                                                                                 | Completion boundary                                                         |
| -------------------- | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Standard             | Integration, release, governance changes, or the current admission's required floor | Exact-source proof and a separately authorized effect                       |
| Routine fast         | Focused repairs, documentation edits, and development feedback                      | Selected tests and gates; omitted acceptance obligations remain open        |
| Authorized emergency | A human-approved temporary bypass of a specific blocked operation                   | Recorded local effect, preserved recovery and explicit pending verification |

The [verification command reference](docs/reference/command-plane.md#standard-and-fast-verification)
owns commands, guarantees, escalation and temporary hook bypass. The routine
fast path is not an emergency exception; neither path silently lowers the
repository's acceptance floor. Automatic risk-selected small-change acceptance
is not yet generally available.

### Shared Source Formatting

Use the selected installed runtime's `ethos format` operation for authored
Markdown, YAML and TOML rather than copying a formatter controller into the
repository. See [native source formatting](docs/guides/quickstart.md#native-source-formatting)
for literal selection, preview, nonmutating check and admitted apply. Formatting
is not complete quality proof; official OpenSpec, generated files and lockfiles
retain their native owners.

### Standard Verification

Start with current `ethos status --json` and its selected owner. Obtain exact-path
`ethos lane prewrite` admission before editing. For each repair:

1. Reproduce the violated invariant through its existing owner.
2. Find every test consumer of the changed modules across the whole test tree,
   including sibling semantic packages and shared fixtures. Directory proximity
   is not dependency coverage. Fixtures must supply the real consumed contract;
   retain their original behavioral assertions.
3. Run those focused consumers and inexpensive format, type, scope and artifact
   checks before starting a complete proof. Do not run a standalone full test
   suite immediately followed by another full proof of the same inputs.
4. Freeze the complete non-ignored source input, including docs and task files,
   then execute the required exact-HEAD proof once. Update progress only after
   its terminal result; a changed source snapshot invalidates the frozen run.
5. Attribute each failed gate to its direct cause or failed prerequisite. Return
   to the smallest failing consumer before any full retry. Preserve the original
   failed evidence instead of combining partial outputs into a passing proof.

Use the current runtime's required proof, archive, acceptance, installation and
publication decisions. Focused checks, signatures and local source acceptance
are separate claims, not substitutes for the requested complete delivery.

### Routine Fast Iteration

1. Reuse the owned Work Lane and active Change; do not create another merely
   for a small edit. Obtain current exact-path prewrite admission.
2. Run the original formatter and the directly affected tests. Include sibling
   consumers when the changed contract is shared.
3. Execute only the selected host gates for development feedback. Inspect their
   terminal results; a read-only plan or readiness result is not execution.
4. Freeze and commit the complete source once the slice is ready. Request the
   required exact-source proof at the acceptance boundary, not after every edit.

Escalate to standard verification when ownership or impact is unresolved, a
shared contract changes, or current admission requires a broader floor. A
non-host `--gate` selection cannot accept an omitted required gate.

### Authorized Emergency Operations

Temporary hook bypass is available through Git's command-scoped configuration,
not a permanent disable or a new ETHOS wrapper. Use it only for the exact
human-authorized operation, with recovery retained and unproved obligations
recorded in the existing Change. Keep signing enabled and verify the actual
effect before retrying. See the [bypass procedure](docs/reference/command-plane.md#authorized-temporary-hook-bypass).
