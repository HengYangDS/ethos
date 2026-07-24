## Context

The hosted GitLab verify job has two different trust boundaries. Bootstrap must
run as root because it installs the checksum-pinned Node runtime beneath
`/usr/local` and maintains a persistent tool cache. The source-budget worker,
however, must run as a real unprivileged Linux identity with no effective or
permitted capabilities so its exact process-count limit remains truthful.

The accepted `32f66ffed` checkout reproduced this mismatch in GitLab job
`26847`: all 17 worker-facing failures carried the stable
`source_budget_worker_isolation_unsupported` gap. Running representative tests
from that same checkout and virtual environment as UID/GID 1000 removed the
isolation failures. The official Python image already provides numeric
UID/GID 65534, avoiding a dependency on image-specific account creation.

The first complete non-root replay then found a second boundary failure. The
local emulator made an independent checkout with `git clone --no-local` from
the root-owned source. The caller accepted the source through a narrow
`safe.directory` overlay, but the clone's child `upload-pack` did not inherit
that command context and rejected the source `.git` as dubious. A direct
source-side `git bundle create`, followed by fetch into a new repository, keeps
all source trust evaluation in the admitted caller process.

Once every test completed, Linux coverage also showed that several Darwin
success paths were covered only by an actual Darwin run. Synthetic contracts
were therefore added for libproc binding, valid group enumeration,
non-privileged telemetry, signal forwarding, and settled permission-denial
cleanup. They test platform contracts rather than pretending Linux provides
Darwin runtime evidence.

## Goals / Non-Goals

**Goals:**

- Preserve root-only bootstrap while making the pytest process and every nested
  worker genuinely unprivileged.
- Fail before pytest when the UID/GID pair, root launcher, or `setpriv`
  capability is invalid.
- Keep generated evidence, cache, and temporary paths writable without making
  the tracked checkout generally writable.
- Keep local emulator source materialization independent, real-Git, and usable
  when the source checkout has a different owner.
- Preserve the existing source-budget contract and 100% cross-platform branch
  coverage.

**Non-Goals:**

- Making the entire GitLab job non-root.
- Replacing GitLab Runner, Docker, or the provider image.
- Adding a general sandbox or weakening fail-closed worker admission.
- Treating local Docker replay as hosted-provider success.

## Decisions

1. **Drop privilege only at the pytest boundary.** The owner script accepts
   `ETHOS_TEST_RUN_AS_UID` and `ETHOS_TEST_RUN_AS_GID` only as a complete pair of
   positive decimal integers. It requires a root launcher and `setpriv`, then
   invokes pytest with `--reuid`, `--regid`, and `--clear-groups`. The worker's
   existing UID/capability admission remains the final fail-closed check.
2. **Use the image's numeric nobody identity.** GitLab projects `65534:65534`
   only into `ethos:verify`. Numeric identity avoids passwd-database coupling
   while remaining present and unprivileged in `python:3.14`.
3. **Transfer only generated runtime ownership.** Root creates and recursively
   transfers `build/`, coverage/JUnit directories, the pytest base temp, and an
   isolated HOME/cache beneath the temporary root. Tracked source remains
   read-only to the test identity, and the owner script restores root ownership
   of generated build and pytest temporary paths before later job stages run.
4. **Consume the identity pair before pytest.** Nested test fixtures that invoke
   owner scripts inherit an already-unprivileged process and must not attempt a
   second root-only drop. The run-as variables are therefore unset before the
   pytest child starts.
5. **Preserve only narrow Git execution overlays.** The repository root and its
   `.git` directory are admitted as safe for the ownership-crossing test
   process, and `core.fsmonitor=false` is appended without deleting those
   overlays. No global wildcard trust is introduced.
6. **Use bundle transport for emulator materialization.** The source process
   writes a temporary bundle for `HEAD`; a new repository fetches and checks out
   that bundle, applies the tracked binary diff, and atomically replaces the
   prior materialization. The temporary bundle is removed on success and
   failure, with no alternates or external object dependency.
7. **Test outcomes, not platform accidents.** An admitted exact-ceiling sample
   may produce the full contract vector on a platform with sufficient runtime
   headroom. If actual memory or recursion exhaustion occurs, the public result
   must remain the stable resource-exhausted gap with no partial coordinates.
8. **Make cross-platform coverage deterministic.** Linux tests explicitly drive
   Darwin adapter success branches through doubles; they do not claim actual
   Darwin kernel or libproc execution.

## Risks / Trade-offs

- **Recursive ownership changes under `build/` add setup cost** -> constrain the
  transfer to ignored generated runtime paths and keep persistent root caches
  outside the unprivileged boundary.
- **Numeric UID/GID may differ in a future image** -> the projection is explicit,
  the owner script validates it, and hosted failure remains observable rather
  than silently falling back to root.
- **Safe-directory overlays could become too broad** -> admit only the exact
  checkout root and exact `.git` path and retain the test helper's filtering of
  unrelated Git identity configuration.
- **Bundle creation adds a temporary artifact** -> keep it under ignored runtime
  state and remove it in a `finally` path before returning evidence.
- **Synthetic Darwin tests could overclaim portability** -> limit them to pure
  adapter contracts and continue requiring actual Darwin proof separately.

## Migration Plan

1. Add RED contracts for paired identity admission, GitLab projection, and
   ownership-crossing emulator materialization.
2. Implement the owner-script privilege boundary and bundle materializer.
3. Replay the complete GitLab verify test gate in the same Linux image with
   root bootstrap and UID/GID 65534 pytest execution.
4. Add deterministic missing platform contracts and repeat the complete replay
   to 100% coverage.
5. Bind the active claim, validate/archive the carrier, refresh onto the current
   candidate, run exact-HEAD proof, and land only the owned Work Lane.
6. Publish governed refs and require fresh exact-SHA hosted observations before
   final record sealing.

Rollback removes the GitLab UID/GID projection and owner-script drop boundary,
restores clone materialization, and reverts the test corrections. Such a
rollback also restores the known GitLab isolation failure and therefore cannot
be described as a healthy verify state.

## Open Questions

None. Hosted successor results remain evidence to collect after publication.
