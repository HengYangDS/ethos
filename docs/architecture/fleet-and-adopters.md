---
subject: ethos:fleet-adopters
role: explanation
state: canonical
relations:
  canonical_for: external repository governance
---

# Fleet And Adopters

ETHOS is the product; governed repositories are adopters. A fleet is a set of
external repository roots plus their tracked governance surfaces.

`ethos fleet inspect --target <repo> --json` reads an adopter in place and
reports whether `.ethos/profile.toml`, referenced configuration, OpenSpec
records, repo-local skills, docs, claims, and evidence are present. The
inspection is data-driven: adopter names, domain contracts, branch roles,
assistant surfaces, and hosted providers belong in the adopter repository or
profile.

For an existing repository, fleet onboarding begins with a strict dry-run. If
the plan finds differing adopter-owned governance files, the owner can choose
`ethos adopt --overlay` explicitly. Overlay is not a force mode: it preserves
the adopter-owned files, exposes their digests in command JSON, and still
rejects conflicting ETHOS-owned binding surfaces. A fleet record becomes
adoption evidence only after the adopter's own tracked profile and
profile-appropriate proof exist.

When an adopter uses non-default branch names, its tracked
`.ethos/workspace.toml` must map the existing release, accepted, candidate,
work, and submit roles. The mapping preserves ETHOS transition semantics while
leaving branch names and branch-provider policy under adopter authority.

This keeps ETHOS core reusable. A domain-specific repository can declare its
own data contracts, assistant projections, intake adapters, and OpenSpec
changes in its tracked profile and configuration without adding that domain's
terms to product packages.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), [Glossary](../reference/glossary.md), [Repository Profile Contract](../governance/repository-profile-contract.md), and [Adopter Boundary And Retirement](../governance/adopter-boundary-and-retirement.md).
