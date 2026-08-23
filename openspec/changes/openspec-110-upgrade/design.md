## Context

`package.json` and `package-lock.json` are the sole executable dependency
authority for the OpenSpec adapter. The adapter derives the expected version
from those declarations and rejects ambient or mismatched executables.

## Goals / Non-Goals

**Goals:**

- Resolve exact OpenSpec 1.10.0 bytes from the canonical npm registry.
- Keep package declaration, lockfile, current contracts, tests, and runtime
  observation consistent.
- Exercise the official interfaces ETHOS consumes before archive.

**Non-Goals:**

- No lifecycle semantics or adapter redesign in this Change.
- No rewrite of historical archived records.
- No unrelated Python, Action, image, or downloaded-tool upgrade.

## Decisions

1. **Upgrade before owner compression.** Lifecycle deletion will target the
   current official interface rather than coding against obsolete 1.9 output.
2. **Keep one exact declaration.** The package and lockfile identify 1.10.0;
   adapter constants continue to derive from them rather than adding a version
   setting.
3. **Preserve history.** Only current contracts and executable expectations
   change. Archived references remain evidence of their original execution.

## Risks / Trade-offs

- Official payload or archive behavior may have changed. Focused real archive
  execution plus strict validation and doctor detect incompatibility.
- Local npm registry configuration may rewrite resolved URLs. The lock is
  regenerated explicitly against `https://registry.npmjs.org/`.

## Migration Plan

1. Capture `npm outdated` and the old archive expectation as RED evidence.
2. Regenerate the exact lock against the canonical registry.
3. Update current contract and test references.
4. Run focused tests, official validation/doctor, and the normal ETHOS proof
   and archive lifecycle.

## Observed Supply-Chain Successor Inputs

The repository-wide freshness audit is broader than this bounded dependency
change. At the frozen pre-proof boundary it reports:

- no outdated direct npm dependency after resolving OpenSpec 1.10.0;
- nineteen Python lock updates from `uv lock --upgrade --dry-run`;
- five distinct GitHub Action commit pins requiring upstream stable-release
  resolution;
- repeated uv image/version projections plus pinned Node, Syft, lychee,
  actionlint, and gitleaks downloads requiring one declaration-to-projection
  freshness audit.

These are successor inputs, not completion claims. They remain separate so
this Change can prove one dependency identity without silently widening its
authority or retaining an unfinished mega-change.
