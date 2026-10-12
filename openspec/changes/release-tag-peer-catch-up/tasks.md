## 1. Release-tag catch-up admission

- [ ] 1.1 Reproduce the missed-peer refusal through public native pre-push and `ethos publish` regressions; verify they fail on the tag source before the change.
- [ ] 1.2 Resolve an existing tag object's release commit from its validated release effect and share it across push admission, publication proof and receipt checks; verify the missed-peer journey publishes the identical object once, attests the selected peer and repeats as an idempotent no-op.
- [ ] 1.3 Verify that a re-signed or unsigned local object, an untrusted signer, a divergent peer tag and a release commit outside accepted history are refused without a peer effect.
- [ ] 1.4 Run the focused release and publication suites with Ruff, Ty, module-layout, repository hygiene and code-size checks on the lane head.

## 2. Adopter Delivery

- [ ] 2.1 With user authorization, bind openai-responses-proxy to a runtime built from its runtime source plus this change; verify its profile stays valid and the v5.0.2 GitLab publication preview passes.
- [ ] 2.2 With user authorization, publish `refs/tags/v5.0.2` to GitLab through `ethos publish`; verify identical peer tag objects and a passing provenance check in the next GitLab pipeline.
