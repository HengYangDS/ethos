---
Subject: ethos-adapters
Role: target product package
State: active
Relations: owns provider-specific integrations
---

# ethos-adapters

Subject: provider-specific integrations and command execution boundaries.

Role: observe, execute, translate, and bind evidence for Git command execution,
SQLite, OpenSpec, GitLab, GitHub, MCP, ACP, Superpowers, pytest, Ruff, and
other providers.

State: target package home.

Relation: adapters do not own ETHOS product semantics. Git branch, ref,
worktree, and commit semantics are native ETHOS repository semantics; this
package owns only execution and projection around them.
