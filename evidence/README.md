# evidence/

`evidence/` is tracked proof. It owns claim records, release manifests,
security proof, attestations, and judged chronicle entries.

The terminal design removes `docs/evidence/` as a proof root and moves the
`claims/` root here. Generated raw streams stay under ignored `.ethos/` and may
be summarized into tracked evidence after review.

| Subdir | Duty |
| --- | --- |
| `claims/` | Trust-bearing claim records (migrated from the legacy `claims/` root). |
| `manifests/` | Release and artifact manifests. |
| `releases/` | Per-version release evidence. |
| `security/` | Security proof (vuln scans, secret scans). |
| `attestations/` | in-toto / SLSA provenance envelopes. |
| `chronicle/` | Judged history and supersession records. |

Authority: docs/architecture/terminal-governance-product-design.md (§`evidence/`).
Migration state (Phase A): directory skeleton created; content relocation from
`claims/` and `docs/evidence/` is a separate, independently-revertible step.
