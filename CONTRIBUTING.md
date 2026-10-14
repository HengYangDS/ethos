# Contributing

ETHOS accepts changes through the `ethos ...` command plane and signed Git
history.

## Identity

Use your own organization-approved Git identity. ETHOS does not require a
single built-in author or a tracked identity allowlist. Git author and committer,
the Work Lane actor, the trusted signing principal, transport credentials, and
forge verification are separate facts. Configure your local identity and signer
through Git; the repository's tracked `[commit_policy]` owns only subject syntax
and whether generated commits require SSH signing.

```bash
git config user.name "<your-name-or-team>"
git config user.email "<your-approved-email>"
git config commit.gpgsign true
git config gpg.format ssh
```

SSH signing is required for generated commits in this repository. ETHOS verifies
the resulting Git object against the configured external trust anchor; it does
not turn author metadata into mutation authority.

## Commit Messages

Use this repository's [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
convention. The tracked [commit policy](.ethos/workspace.toml) owns the accepted
subject syntax:

```text
<type>: <description>
<type>(<scope>): <description>
```

- `type` identifies the kind of change: `feat`, `fix`, `docs`, `test`,
  `refactor`, `perf`, `build`, `ci`, `chore` or `revert`.
- `scope` is optional. When present, keep the literal parentheses and name the
  affected semantic area, such as `proof`, `lanes` or `cli`. The current policy
  accepts nonempty lowercase ASCII letters, digits and hyphens in this field.
- `description` is a nonempty summary after the colon and space.

```text
feat(proof): add evidence gate runner
fix(lanes): reject stale integration requests
docs(cli): clarify fast verification
ci: add GitLab verification pipeline
```

For an incompatible change, add a `BREAKING CHANGE: ...` footer explaining the
incompatibility and migration. The current subject policy does not accept the
optional `!` spelling. Commit syntax alone does not establish SemVer or release
compliance; [release governance](docs/governance/release-governance.md#semantic-versioning-and-changelog)
owns those obligations.

Avoid vague subjects such as `Update files` or product claims without evidence.

## Verification

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
