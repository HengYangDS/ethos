# evidence/

`evidence/` is the tracked durable-evidence root for ETHOS. Current evidence is
carried only by Attestations. Retained Claims, Chronicle entries, and parity files
are immutable historical bytes with no current producer or authority.

Generated raw streams stay under ignored local state such as `.ethos/` or build
artifacts. They become repository truth only after review promotes a bounded
result into `evidence/attestations/` with verifier, scope, digest, and HEAD bindings.

## Promotion Path

Machine evidence starts in ignored generated homes such as `build/evidence/` or
`build/ethos/`. Promotion is an explicit review act, not a move or copy by
directory convention. A promoted record must preserve the command, scope,
verifier, digest, HEAD, and bounded verdict in an Attestation. `docs/evidence/`
may present curated summaries but is not a proof root.

Runtime caches (`.cache/local-state/`, `.ethos/state/`,
`build/runtime/tool-cache/`, `build/runtime/work/`) and local artifacts
(`build/artifacts/`) are outside the promotion path. They are deleted or
regenerated, not summarized as proof.

## Layout

| Path | Duty |
| --- | --- |
| `README.md` | Human index for the evidence root. This file is not proof by itself. |
| `attestations/` | Current durable, content-addressed Attestations. |
| `claims/` | Immutable historical Claim bytes; no current producer or authority. |
| `chronicle/` | Immutable historical judged records; no current producer or authority. |
| `parity/` | Immutable historical parity bytes; no current producer or authority. |

Do not add another current evidence class or pre-create empty taxonomy directories.
New evidence meaning must use the Attestation contract or be admitted by a
superseding design change.

## Boundary Rules

- Keep `evidence/` root shallow: only this README and owned subdirectories.
- Put current durable evidence only under `evidence/attestations/`.
- Preserve `claims/`, `chronicle/`, and `parity/` bytes as history; do not use
  them to mint current verdicts or authorize mutation.
- Do not treat runtime logs, command streams, local caches, or build outputs as
  evidence until a reviewed Attestation binds them.

Authority: docs/plans/terminal-governance-product-design.md (§`evidence/`).
