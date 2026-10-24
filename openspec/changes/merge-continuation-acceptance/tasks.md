# Tasks

## 4. Archive and Integration Integrity

- 4.16 Withdrawn by DR-0016 (in-repo). Qualify native merge continuation and original-request recovery through full proof, installed CLI and rollback; verify lost ACK, runtime upgrade, complete original request/plan custody, fresh authority, unchanged parents/content and no recompilation or CAS replay. Preserve Python 3.12–3.14, original custody `32c4f656e92ac` and prior local acceptance `minimal-native-breakglass.host-cli.acceptance.json` / `native-installed-continuation-20261014T0651.acceptance.json`; missing bindings stay UNKNOWN and metadata-only quit proves no original effect.
- [x] 4.18 Close this Change on its delivered scope: DR-0016 withdraws 4.16 and 13.4.4 from 0.2.0 and records when each returns. Evidence: `docs/decisions/dr-0016-change-closure-scope.md`.

## 13. Feedback-Driven Improvement Closure

- 13.4.4 Withdrawn by DR-0016 (in-repo). Deliver native stat-cache refresh; verify dirty-byte conservation, public closeout, exact proof and installed behavior. Focused source tests do not establish delivery.
  - 13.4.4.1 Withdrawn by DR-0016 (in-repo). Recover materialization from the original admitted plan and Attestation without recompilation or CAS replay; verify transition/primitive identity, complete public recovery, exact proof and installed replay while preserving failed custody.

## Workflow follow-up

- After 4.16 installed acceptance and the original merge finish, retire its temporary delivery lane through current native admission; preserve unique evidence first.
- Prove the exact head, archive this Change, prove the archived head, then land, close out and publish.
- On 2026-10-24 [DR-0016](../../../docs/decisions/dr-0016-change-closure-scope.md) withdrew the tasks that this Change did not deliver from 0.2.0; their lines stay in this file without checkboxes.
