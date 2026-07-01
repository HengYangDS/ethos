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

Profiles generate the adopter governance skeleton:

```text
.ethos/
.agents/skills/
openspec/
docs/
docs/evidence/
claims/
```

GitHub and GitLab profiles also generate hosted-CI projections and declare
those projections under `.ethos/release.toml` host-profile surfaces. The kernel
remains profile-free; repository-specific contracts stay in adopter profiles.

An adopted repository runs the `adopter_repository` posture of the same
single-kernel dual-posture model used by ETHOS self-governance. Generated rules
use `ethos report --json` for governance audit and `ethos prove --json` for
proof readiness. `ethos self audit` remains a self-hosting depth command for
the product repository, not the default adopter governance gate.
