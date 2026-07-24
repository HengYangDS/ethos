## Why

GitLab's Docker executor starts the `python:3.14` verify job as root. ETHOS's
Linux source-budget worker correctly rejects UID 0 or retained resource
capabilities because `RLIMIT_NPROC` is not enforceable for that identity. At
accepted commit `32f66ffed`, GitLab job `26847` therefore returned 17
`source_budget_worker_isolation_unsupported` failures even though the same
checkout and environment passed the representative worker contracts after the
test process ran as an unprivileged identity.

Moving the whole job to a non-root container user would break the deliberate
root bootstrap boundary used to install Node and populate persistent caches.
The verify job instead needs an owner-script boundary that keeps bootstrap as
root, prepares only governed runtime paths, and drops privilege only for
pytest. That boundary also exposed two portability defects: local emulator
materialization used a source-side local clone whose child `upload-pack` lost
the caller's trusted-directory overlay, and Linux coverage depended on Darwin
success paths being exercised only on a Darwin host.

## What Changes

- Add a paired, validated UID/GID input to the Python test owner script and use
  `setpriv` to run only pytest as the image's numeric `nobody` identity.
- Prepare and transfer ownership only for generated `build/` and temporary test
  paths, preserve narrow Git safe-directory overlays, and consume the identity
  inputs before nested owner-script calls.
- Project UID/GID `65534` only into GitLab's repository-proof job while leaving
  root bootstrap, persistent tool caches, GitHub, and ordinary local execution
  unchanged.
- Materialize local emulator sources through a temporary Git bundle followed
  by an independent fetch/checkout, avoiding source-side clone ownership
  revalidation while retaining a real standalone `.git` directory.
- Correct the exact-ceiling resource acceptance test to enforce the existing
  contract: valid input may complete, while actual memory or recursion
  exhaustion must fail atomically without partial coordinates.
- Add deterministic cross-platform backend and cleanup contracts so the Linux
  hosted gate reaches the repository's 100% branch-coverage floor without
  borrowing Darwin-host execution.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: subject=gitlab-nonroot-verify; reuse=extend; change=modify;
  facet:lifecycle=validation; facet:surface=ci,test,emulator,openspec,evidence;
  facet:authority=source,test,openspec,claim,evidence

## Out Of Scope

- Changing the GitLab Runner service, Docker daemon, executor privilege mode,
  or the base image.
- Running bootstrap, Node installation, or persistent-cache population as the
  unprivileged test identity.
- Weakening Linux worker resource admission, bypassing `RLIMIT_NPROC`, retaining
  capabilities, or treating an isolation-unsupported result as success.
- Changing GitHub's macOS timeout projection or the repository-wide pytest
  defaults.
- Modifying, landing, retiring, or cleaning any foreign Work Lane.
- Claiming hosted success before fresh GitHub and GitLab runs observe the exact
  published successor commit.

## Impact

The Python test owner script, canonical GitLab template and generated
projection, local emulator materializer, focused architecture and worker
contracts, cross-platform coverage contracts, and bounded OpenSpec/claim/
Chronicle evidence. No dependency, runner-service, or production worker-policy
change.
