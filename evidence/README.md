# evidence/

`evidence/` is tracked proof for ETHOS repository decisions. It stores
claim records, judged chronicle entries, parity evidence, and future release or
attestation proof after review.

Generated raw streams stay under ignored local state such as `.ethos/` or build
artifacts. They become repository truth only after a reviewer promotes a
bounded summary into this tree and binds it from a claim or chronicle record.

## Layout

| Path | Duty |
| --- | --- |
| `README.md` | Human index for the evidence root. This file is not proof by itself. |
| `claims/` | Trust-bearing claim records. Claims bind evidence paths, digests, scope, carriers, and promotion targets. |
| `chronicle/<topic>/<date>.md` | Judged history and dated proof records. Human-readable proof Markdown is topic-scoped so closeout evidence stays reviewable. |
| `parity/` | Machine-readable parity evidence for adopter and shadow comparisons. |

Additional evidence classes such as release manifests, security reports, or
attestations may be added when a real promoted record needs them. Do not create
empty taxonomy directories in advance; use topic directories only when a judged
record exists.

## Boundary Rules

- Keep `evidence/` root shallow: only this README and owned subdirectories.
- Put dated Markdown proof records under `evidence/chronicle/<topic>/<date>.md`.
- Put claim TOML under `evidence/claims/`.
- Put generated parity JSON under `evidence/parity/` only when it is tracked,
  HEAD-bound, and validated by the parity gates.
- Do not treat runtime logs, command streams, local caches, or build outputs as
  evidence until they are summarized into a tracked, reviewable record.

Authority: docs/architecture/terminal-governance-product-design.md (§`evidence/`).
