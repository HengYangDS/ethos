## Context

OpenSpec is mandatory governance in ETHOS, but product truth still lives in
source, tests, schemas, docs, claims, and evidence after closeout. The terminal
design requires active OpenSpec changes to route through live capability names
and state why a change is reuse, extension, extraction, or new work.

Without a machine guard, proposal metadata becomes optional prose. That weakens
the OpenSpec-first planning gate and lets future Work Lanes enter with unclear
owners or duplicated normative surfaces.

## Decision

Extend the official OpenSpec adapter with an ETHOS product protocol review in
lifecycle mode. For each active change, the adapter now reads `proposal.md` and
checks capability bullets under `## Capabilities` for:

- direct live capability names;
- sibling capability profile presence;
- subject, reuse, change, lifecycle facet, surface facet, and authority facet;
- valid reuse and change vocabularies;
- an `## Out Of Scope` section.

The report is added under each lifecycle change as `proposal_protocol`. Gaps
are emitted as `openspec_proposal_*` and `openspec_capability_profile_*` codes.

## Trade-offs

- The parser is intentionally line-oriented and limited to ETHOS proposal
  bullets. That keeps the guard deterministic and avoids turning Markdown into
  a second schema language.
- The adapter validates capability profile shape with local TOML checks instead
  of importing repository schema helpers. That keeps package boundaries clean.

## Rollback

Remove the proposal protocol report from `openspec_native.py` and the related
unit test. Official OpenSpec validation and existing artifact/claim checks keep
working, but proposal metadata drift would become advisory again.

