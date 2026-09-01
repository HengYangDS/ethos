---
subject: ethos:docs-registry
role: explanation
state: canonical
relations:
  canonical_for: documentation governance
---

# Docs Registry

Status: canonical.

Purpose: define one mechanically checkable documentation structure and the
placement rules that keep each current meaning under one owner.

See also: [Documentation Root](../README.md),
[Product Design Contract](product-design-contract.md),
[Terminal Governance Product Design](../plans/terminal-governance-product-design.md),
and [Command Plane](../reference/command-plane.md).

ETHOS documentation is governed as sedimented knowledge, not as a loose page
pile. Every governed document declares Subject, Role, State, and Relation
metadata in front matter.

`ethos prove --gate docs-registry --json` is the reader-facing and machine
quality entrypoint.
Missing metadata is a required gap because agents need to distinguish canonical
truth, active workflow notes, planned material, experimental material, and
archived history before they act.

`ledger` is not a document role. Raw feedback, transcripts, host memory, agent
summaries, generated classifications, and temporary recovery matrices are
non-authorizing inputs. A bounded recovery uses one official OpenSpec Change to
classify each distinct obligation as accepted, superseded, pending verification,
or rejected. Accepted meaning then moves to the Product Design Contract, the
Terminal Governance Product Design, a necessary Decision Record, or its native
executable owner; the recovery material is deleted after coverage proof.

The registry lifecycle is:

```text
observe -> shape -> canonize -> project -> retire
```

Archive material may preserve old vocabulary. Canonical docs must lead with the
single `ethos ...` command plane.

Superseded documents live only as explicit `docs/history/` carriers. Current
architecture, governance, reference, guides, and plan surfaces must not retain
redirect or locator pages for retired concepts; they link directly to the
historical carrier when historical context is necessary. Retirement removes
only the redundant current-surface carrier, never immutable OpenSpec archives
or historical evidence bytes.

## Directory entrypoint rule

`README.md` is retained only when it is the actual index, navigation entrypoint,
or semantic boundary for its directory. A directory with one substantive child
does not receive a README merely because the directory exists; an empty
directory and a marker-only README are removed. If a README contains the only
unique navigation or boundary meaning, absorb that meaning into the owning
document before deleting it.

A Decision Record is admitted only when a choice among alternatives, its
consequences, and its revisit or retirement condition remain useful across more
than one Change and cannot be expressed clearly by the current contract or
source. It is not a feedback receipt, status page, task list, or archive index.
Its filename is lowercase and semantic rather than a numbered identity.

## Portability Boundary

The registry owns portable document metadata, role/state vocabulary, taxonomy
extensions, visible sections, command examples, and plan discoverability. It
reads the documentation root declared by the adopter profile, defaulting to
`docs/`; it does not require ETHOS's physical directories.

ETHOS's own physical documentation shape is a product self-audit concern. It is
not an adopter contract and is not exposed as a second topology gate. An
adopter may organize its documentation by its native subject domains while
retaining the same metadata and authority semantics.
