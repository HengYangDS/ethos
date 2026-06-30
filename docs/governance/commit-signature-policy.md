---
subject: ethos:commit-signature-policy
role: policy
state: canonical
relations:
  canonical_for: signed contribution history
---

# Commit Signature Policy

Maintainer commits use:

```bash
git config user.name "Yang HENG"
git config user.email "heng.yang.ds@hotmail.com"
git config commit.gpgsign true
git config gpg.format ssh
```

Commit subjects follow Conventional Commits. `ethos quality commits --json`
checks local identity and signing configuration; `ethos quality commits
--enforce-head --json` additionally requires the current HEAD subject and
signature to pass release policy. The repository `.mailmap` normalizes
historical author aliases for local history views.
