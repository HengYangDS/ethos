## 1. Release-tag catch-up admission

- [x] 1.1 Reproduce the missed-peer refusal through public native pre-push and `ethos publish` regressions; verify they fail on the tag source before the change.
- [x] 1.2 Resolve an existing tag object's release commit from its validated release effect and share it across push admission, publication proof and receipt checks; verify the missed-peer journey publishes the identical object once, attests the selected peer and repeats as an idempotent no-op.
- [x] 1.3 Verify that a re-signed or unsigned local object, an untrusted signer, a divergent peer tag and a release commit outside accepted history are refused without a peer effect.
- [x] 1.4 Run the focused release and publication suites with Ruff, Ty, module-layout, repository hygiene and code-size checks on the lane head.
  - Ruff, Ty, import-linter and code-size pass at the lane head `a0a9f3f2c`. The focused suites ran there against the accepted root's environment, where four existing killed-release cases fail because the isolated child imports that environment's source instead of the lane's.
  - The same change cherry-picked onto the adopter's runtime source as `ca3143fce` passes all 49 release and publication cases in its own environment, with markdownlint, Prettier, repository hygiene and module-layout. Exact-source full proof is open.

## 2. Adopter Delivery

- [ ] 2.1 With user authorization, bind openai-responses-proxy to a runtime built from its runtime source plus this change; verify its profile stays valid and the v5.0.2 GitLab publication preview passes.
- [ ] 2.2 With user authorization, publish `refs/tags/v5.0.2` to GitLab through `ethos publish`; verify identical peer tag objects and a passing provenance check in the next GitLab pipeline.

## Workflow follow-up

- Peer publication of the adopter's missed tag waits for its GitLab peer to be reachable; at 2026-10-13 01:10 +08:00 it refused the connection.
- Binding openai-responses-proxy to a runtime carrying this change changes shared Git-common hook activation for every live session there; two sessions held valid Work Lane leases at that time. Coordinate before the effect.
