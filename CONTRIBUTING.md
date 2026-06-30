# Contributing

ETHOS accepts changes through the `ethos ...` command plane and signed Git
history.

## Identity

Use this repository identity for commits:

```bash
git config user.name "Yang HENG"
git config user.email "hengyang.2003@tsinghua.org.cn"
git config commit.gpgsign true
git config gpg.format ssh
```

Expected author: `Yang HENG <hengyang.2003@tsinghua.org.cn>`.

SSH signing is required for maintainer commits. The repository includes
`.mailmap` so historical aliases render consistently in local tooling.

## Commit Names

Use Conventional Commits:

```text
feat: add evidence gate runner
fix: reject invalid action graph cycles
docs: refine command-plane reference
ci: add GitLab verification pipeline
```

Avoid vague subjects such as `Update files` or product claims without evidence.

## Verification

Before proposing a change:

```bash
uv run --group dev pytest tests/unit tests/architecture -q
uv run --group dev ruff check .
uv run --package ethos ethos self audit --json
uv run --package ethos ethos report --json
```

Changes that affect package metadata should also run:

```bash
uv build --all-packages
```
