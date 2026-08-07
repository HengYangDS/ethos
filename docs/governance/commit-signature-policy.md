---
subject: ethos:commit-signature-policy
role: policy
state: canonical
relations:
  canonical_for: signed contribution history
---

# Commit Signature Policy

Maintainer and automation commits use the repository's configured
contributor policy rather than a product-hardcoded person:

```bash
git config user.name "<your-name-or-team>"
git config user.email "<your-approved-email>"
git config commit.gpgsign true
git config gpg.format ssh
```

`.ethos/workspace.toml` owns the concrete policy: subject grammar, signing
requirement, signing format, identity mode, and the allowed human, team, and bot
identities. Multi-contributor repositories extend that policy with additional
role-based human, team, reviewer, contributor, service, or bot identities rather
than by hardcoding a product author. Commit subjects follow Conventional
Commits in this repository. `tools/ci/scripts/run-head-bound-proof.sh` checks local identity
membership and signing configuration; `tools/ci/scripts/run-head-bound-proof.sh` additionally requires the current HEAD subject and signature to pass
release policy.

A governed checkout may also enable a local, repository-scoped pre-push identity
policy without turning a person into product authority:

```bash
git config ethos.pushIdentityPolicy configured-user
```

When that policy is enabled, the worktree-local launcher installed by
`ethos hook install` passes the remote tip to the Python hook owner; the hook checks every newly pushed commit in the range and
requires both Git author and Git committer to match the checkout's configured
`user.name` and `user.email`. This is a local admission policy for a repository
or forge account, not tracked historical alias metadata and not a product-wide
built-in author. ETHOS does not use tracked historical alias metadata as a
product governance mechanism.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
