## Context

GitHub dev at `18aa8707` produced a passing repository proof but the wrapper
blocked on missing local candidate/runtime projections. Main could not select
an active Change. GitLab dev stopped at a bare OpenSpec command after tests;
package conformance failed offline interpreter discovery. External-link failure
is independently unclassified because its job trace omitted link diagnostics.

## Decisions

1. Reuse `ethos prove --host --execute` for hosted observation. Preserve the
   existing declared default/full gate sets and their dependency closure; do
   not substitute a handpicked subset. Official OpenSpec validation, the
   quality stage, and native conformance remain separate requirements. Do not
   invent a second registry or claim this observation authorizes local landing.
2. The hosted receipt requires executed passing host checks, exact expected and
   observed HEAD, and unchanged checkout HEAD. Malformed JSON, empty checks,
   failed process, stale coordinates, or repository-attestation masquerading
   as host observation fail closed. Preserve command stderr and required gaps.
3. Use repository-installed OpenSpec explicitly in native provider syntax;
   the gate runner remains the owner of gate toolchain resolution. Do not
   install hooks or fabricate candidate refs in ephemeral hosted checkouts.
4. Runtime tools already have an authenticated Python argument. Project that
   exact path to uv instead of requiring another interpreter on ambient PATH
   or forcing a second managed installation. Keep offline and locked checks.

## Risks And Verification

A green wrapper must not conceal a gate failure or lower the 95 percent coverage
floor. Regress real shell transport with adversarial result envelopes before
repair; verify offline interpreter selection with isolated discovery. Retain
both Forge observations as separate exit criteria after accepted publication.
The main external-link cause remains unverified until diagnostic evidence is
available; do not introduce retries or exclusions by inference.
