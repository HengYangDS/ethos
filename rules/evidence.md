# Evidence Rules

Purpose: define what can support a bounded repository verdict.

| Field | Rule |
| --- | --- |
| Authority | `ethos prove --json`, `ethos status --json`, docs registry, OpenSpec records, Git facts |
| Trigger | Evaluating readiness, assurance, proof, completion, landability, or publishability. |
| Action | Bind the verdict to current command output or an Attestation, exact HEAD, scope, and evidence location. |
| Evidence | Passing command JSON or a tracked Attestation. |
| Stop | Verdict lacks HEAD binding, command, scope, or verifier output. |

## Rules

- Do not claim completion from unit tests alone when the touched path requires
  docs, schema, projection, security, release, or profile-scoped assurance.
- Command JSON is machine evidence; Markdown explains human judgment.
- Generated runtime logs and JSONL streams are not truth until summarized into
  a bounded Attestation.
- Local fallback evidence must be gathered on a stable Git HEAD; if HEAD moves
  during a gate bundle, discard the evidence and rerun on the new head.
- Evidence must distinguish dry-run readiness from executed proof.
