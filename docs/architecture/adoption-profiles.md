---
subject: ethos:adoption-profiles
role: reference
state: canonical
relations:
  canonical_for: repository adoption
---

# Adoption Profiles

`ethos adopt` projects ETHOS into another repository without copying adopter
semantics into ETHOS core.

Supported profiles:

```bash
ethos adopt --profile generic --dry-run
ethos adopt --profile python-package --dry-run
ethos adopt --profile monorepo --dry-run
ethos adopt --profile github --dry-run
ethos adopt --profile gitlab --dry-run
```

Profiles generate `.ethos/` config and optional hosted-CI projections. The
kernel remains profile-free.
