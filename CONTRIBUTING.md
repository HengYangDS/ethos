# Contributing

ETHOS accepts changes through the `ethos ...` command plane and signed Git
history.

## Identity

Use your own organization-approved Git identity. ETHOS does not require a
single built-in author. This repository's accepted humans, teams, and automation
accounts are declared in `.ethos/workspace.toml` under `[commit_policy]` and
`[[commit_policy.allowed_identities]]`. In multi-contributor repositories,
add or delegate through role-based team, contributor, reviewer, maintainer, and
automation entries instead of changing ETHOS product code or assuming a single
author.

```bash
git config user.name "<your-name-or-team>"
git config user.email "<your-approved-email>"
git config commit.gpgsign true
git config gpg.format ssh
```

SSH signing is required for maintainer and automation commits in this
repository. ETHOS validates current commit identity, role allowlist membership,
and signing policy directly instead of normalizing historical aliases through
tracked repository metadata.

## Commit Names

Use Conventional Commits:

```text
feat: add evidence gate runner
fix: reject cyclic PlanIR dependencies
docs: refine command-plane reference
ci: add GitLab verification pipeline
```

Avoid vague subjects such as `Update files` or product claims without evidence.

## Verification

Before proposing a change:

```bash
tools/ci/scripts/run-python-tests.sh
tools/ci/scripts/run-python-lint.sh
uv run ethos status --json
uv run ethos plan --changed --json
uv run ethos prove --json
```

Changes that affect package metadata should also run:

```bash
uv build --out-dir build/artifacts/python --clear --no-create-gitignore
```
