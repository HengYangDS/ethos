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
uv run --frozen --offline python -m nox -s tests
uv run --frozen --offline python -m nox -s lint
uv run ethos status --json
uv run ethos plan --changed --json
uv run ethos prove --json
```

Changes that affect package metadata should also run:

```bash
uv run --frozen --offline python -m nox -s build
```
