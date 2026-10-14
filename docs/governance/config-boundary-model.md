---
subject: ethos:config-boundary-model
role: policy
state: canonical
relations:
  canonical_for: .ethos, .config, rules, docs, and system placement boundaries
---

# Config Boundary Model

ETHOS separates repository binding, execution configuration, rules, evidence,
and machine contracts. No single directory owns every governance fact.

## Placement Matrix

| Surface                   | Role                              | Owns                                                                                   | Does Not Own                                                                                                             |
| ------------------------- | --------------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `.ethos/`                 | ETHOS binding layer               | tracked repository binding: profile, workspace, release and rules                      | change intent, tool-native config, domain truth, durable evidence, mutable runtime state                                 |
| `<git-common-dir>/ethos/` | repository-local coordination     | leases, bounded requests, operation receipts and transaction state shared by worktrees | durable Attestation selection, product meaning, portable configuration or a required per-repository product installation |
| `.config/`                | tool-native configuration         | declared tool policy, boundary configuration and configuration references              | business scripts, tool implementation, documentation, ETHOS ontology, evidence truth or user decisions                   |
| `rules/`                  | governance rule layer             | human and agent rules, domain contracts, projection policies                           | tool implementation details, generated state                                                                             |
| `docs/`                   | explanation layer                 | canonical docs, decisions, reference material                                          | local runtime state, durable evidence ownership                                                                          |
| `system/`                 | optional machine-contract layer   | machine-readable product or system contracts                                           | adopter-only domain truth when absent                                                                                    |
| `openspec/`               | accepted intent and specification | official OpenSpec Changes, accepted specs and native lifecycle                         | execution authority, runtime state or proof by itself                                                                    |
| `.agents/`                | repo-local agent projection       | skills and activation projections                                                      | independent truth store                                                                                                  |

## `.ethos/` And `.config/`

`.ethos/profile.toml` references `.config/`; it does not replace it.

`.config/` remains the repository-native location for how tools run. The
[ETHOS source repository paradigm](../decisions/dr-0012-repository-paradigm.md "source-only") fixes its
layout for every governed repository. Tool configuration lives under
`.config/checks/<owner>/`, `.config/release/<owner>/`, `.config/ci/` or the
toolchain roots (`.config/mise/` and the package-manager roots it binds).
`<owner>` names the consuming tool, or a repository check when only
repository-owned parameters exist. Native files keep the tool's canonical
basename and use TOML when the tool reads TOML, and repository-owned parameters
are `policy.toml`. Every file under `.config/` has a consuming tool or check;
explanation, scripts and evidence live with their own owners. Invocations pass
these paths explicitly, so no root pointer file is needed. A profile may
reference these carriers but does not copy their contents.

CLI, SDK, MCP and hook consumers select one installed product; repository-local
coordination is not a mandatory product copy. Read-only selected inputs retain
their canonical hierarchy and owners under the package resource boundary.
Durable Attestations remain selected by `refs/ethos/attestations-set`; local
operation receipts have separate bounded recovery lifetimes.

## `system/` Optionality

Product repositories may expose machine contracts under `system/`. Adopter
repositories are not required to have a `system/` tree. ETHOS must work from the
repository profile, configuration roots, official intent and Git-native
Attestations when no system contract layer exists.

If `system/` exists, ETHOS may treat it as a machine-contract surface according
to the repository authority order. If it is absent, absence is not a profile gap
unless the profile explicitly requires it.

## Tool Boundary

A tool configuration file decides how one tool runs. A tool catalog or profile
binding decides why the tool runs for a repository operation. Hosted CI files are
provider projections over repository-owned scripts and policies; they do not
replace local proof or repository evidence.

Status: see front matter.

Purpose: keep configuration placement MECE as ETHOS adoption expands across
repositories with different shapes and toolchains.

See also: [Repository Profile Contract](repository-profile-contract.md),
[Product Design Contract](product-design-contract.md),
[ETHOS source DR-0012: Repository paradigm](../decisions/dr-0012-repository-paradigm.md "source-only"), and
[ETHOS source Terminal Governance Product Design](../plans/terminal-governance-product-design.md "source-only").
