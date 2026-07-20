## Context

ETHOS profiles are the adopter binding, not a copy of adopter truth. The
current strict schema intentionally rejects unknown fields and `.` as a
repository path. An older DDWG profile contains retired identity fields and
uses `roots.rules = "."` to mean one root-level normative document. The first
property is a compatibility problem; the second is an authority-model problem.

Several public command paths call profile helpers which raise `ValueError` for
an invalid declaration. This leaks an implementation exception through JSON
surfaces and prevents callers from receiving `ok=false` plus a stable required
gap.

## Goals / Non-Goals

**Goals:**

- Preserve strict current declarations while admitting one explicit legacy
  normalization shape.
- Model a single root-level normative file truthfully.
- Return structured fail-closed results for invalid-profile reader and
  lifecycle operations.
- Keep the profile parser as the single source of migration semantics.

**Non-Goals:**

- Reintroducing arbitrary legacy tables, permissive unknown fields, or
  repository-type-specific profiles.
- Creating, relocating, or mirroring an adopter's rules files.
- Mutating any adopter in the ETHOS product change.
- Treating local proof, remote publication, or hosted CI as interchangeable.

## Decisions

1. **Normalize only the known former declaration.** The loader recognizes the
   retired `schema_version`, `profile_version`, `ethos_contract_version`, and
   `[repository]` metadata only when their values match the historical shape;
   all other unknown or malformed fields remain invalid. This offers a bounded
   migration bridge rather than a second schema.
2. **Introduce `normative_sources`.** It is an optional non-empty tuple of
   repository-relative files. `roots.rules` remains a directory-like
   repository root and continues to reject `.`. Evidence-root calculation adds
   the declared normative sources; it never treats a file as a directory.
3. **Translate invalid profiles at the public boundary.** Domain helpers may
   remain fail-closed internally, but command/report composition must catch the
   known invalid-profile condition and emit an `EthosResult` with
   `adopter_profile_invalid:.ethos/profile.toml`. JSON consumers then always
   receive a parseable result and an enforcing command still exits non-zero.

## Risks / Trade-offs

- **Legacy normalization accidentally becomes permissive** -> normalize only
  exact retired fields and test negative variants.
- **A file source is treated as a directory by downstream consumers** -> keep
  `normative_sources` separate from `roots.rules` and test root candidates.
- **A new command path leaks a traceback or masks the binding defect** ->
  centralize translation in the public CLI boundary and make `land` validate
  its target adopter before mutation admission. Cover orient, report, plan,
  prove, OpenSpec lifecycle, and both read-only and applying land surfaces.

## Migration Plan

1. Add the typed compatibility and error-result contract with tests.
2. Prove it in the ETHOS work lane and land it through the normal lifecycle.
3. In a separate DDWG Change, replace its old declaration with the canonical
   current shape plus `normative_sources = ["guidelines.md"]`.
4. Execute DDWG's real repository-bound proof and closeout before separately
   reconciling GitLab and GitHub.
