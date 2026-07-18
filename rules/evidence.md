# Evidence Rules

Purpose: define what can support a repository truth claim.

| Field | Rule |
| --- | --- |
| Authority | `ethos prove --json`, `ethos report --json`, docs registry, OpenSpec records, Git facts |
| Trigger | Claiming readiness, parity, proof, completion, landability, or publishability. |
| Action | Bind the claim to command output, HEAD, scope, and evidence location. |
| Evidence | Passing command JSON or tracked evidence manifest. |
| Stop | Claim lacks HEAD binding, command, scope, or verifier output. |

## Rules

- Do not claim completion from unit tests alone when the touched path requires
  docs, schema, projection, security, release, or parity proof.
- Command JSON is machine evidence; Markdown explains human judgment.
- Generated runtime logs and JSONL streams are not truth until summarized into
  tracked evidence.
- Local fallback evidence must be gathered on a stable Git HEAD; if HEAD moves
  during a gate bundle, discard the evidence and rerun on the new head.
- Evidence must distinguish dry-run readiness from executed proof.
