---
subject: ethos:fleet-adopters
role: explanation
state: canonical
relations:
  canonical_for: external repository governance
---

# Fleet And Adopters

ETHOS is the product; governed repositories are adopters. A fleet is a set of
external repository roots and their independently tracked facts.

`ethos fleet inspect --target <repo> --json` reads an adopter in place. It
separates the required `.ethos/profile.toml` binding from optional capabilities
such as OpenSpec, skills, docs, claims, evidence, and provider projections.
Missing optional capabilities do not invalidate the binding.

Fleet onboarding starts with `ethos adopt --root <repo> --json`, which plans only
the binding manifest. Existing repository files remain untouched. A differing
nonempty binding fails closed; ETHOS provides no overlay or force mode. Apply
requires explicit authorization and a matching Git HEAD.

Repository-specific branch roles, domain contracts, assistant surfaces,
tool-native configuration, and hosted providers stay under adopter authority.
Later capability commands may project those surfaces explicitly, but the
adoption bootstrap does not reserve directories or generate provider files.

This keeps the kernel reusable: every adopter receives the same lifecycle
semantics while supplying its own facts and gates through the one typed profile
contract.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), [Glossary](../reference/glossary.md), [Repository Profile Contract](../governance/repository-profile-contract.md), and [Adopter Boundary And Retirement](../governance/adopter-boundary-and-retirement.md).
