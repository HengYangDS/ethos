---
subject: ethos:fleet-adopters
role: reference
state: canonical
relations:
  canonical_for: external repository governance
---

# Fleet And Adopters

ETHOS is the product; governed repositories are adopters. A fleet is a set of
external repository roots plus their tracked governance surfaces.

`ethos fleet inspect --target <repo> --json` reads an adopter in place and
reports whether `.ethos`, OpenSpec records, repo-local skills, docs, claims, and
evidence are present. The inspection is data-driven: adopter names, domain
contracts, branch roles, assistant surfaces, and hosted providers belong in the
adopter repository or profile.

This keeps ETHOS core reusable. A dmgr-style repository can declare raw/cache
contracts, assistant projections, Backlog intake, and OpenSpec changes in its
own tracked profile without adding dmgr terms to product packages.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
