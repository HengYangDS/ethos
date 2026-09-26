## Why

The accepted ETHOS source changed locked Python and npm inputs, but GitLab CI
still uses an immutable supply image built from the previous inputs. Its
bootstrap correctly stops at `ci_supply_input_mismatch` before any quality job
can run. Separately, GitHub's relative UV cache path moves when an adopter
quality test changes its working directory, making an offline lock resolution
fail despite the supplied cache. Anchoring that cache exposed a second failure:
the same test still asks a cold hosted runner to resolve a new lockfile offline.
The supply image guarantees locked installation inputs, not package-index
metadata for a fresh solve. Both execution paths must be repaired without
bypassing their checks. A subsequent exact-SHA GitLab run reached its quality
job but spent 180 seconds downloading `mise` from GitHub and stopped at 3%.
The immutable image supplies Python and npm inputs but not the native gate
tools that the hosted proof requires. The runner must verify those tools from
the image, not provision them during a supposedly offline job.
The GitHub run at the same source passed 4,699 tests but timed out one composite
MCP conformance case at the global 120-second per-test limit; that case spans
three real transports and has separate bounded calls. Its incomplete result
cannot qualify hosted verification.

## What Changes

- Build the existing Linux ARM64 supply image from the exact accepted GitHub
  `dev` commit through the trusted workflow, and read back its immutable digest.
- Replace the stale image digest at the existing CUE owner and refresh the
  checked GitLab and CI-emulator projections without changing their command
  graph or weakening the input-hash check.
- Anchor GitHub's UV and CI-tool cache paths to the checkout workspace in CUE,
  regenerate its workflow, and test the child-working-directory boundary.
- Commit the adopter quality sample's project and lockfile as a fixture, so
  its positive and defect cases test the locked toolchain without resolving a
  new lockfile on a hosted runner. Preserve missing-lock and lock-drift cases.
- Build `mise` and the locked native gate tools into the trusted supply image,
  bind their source inputs in its manifest, and exercise the complete tool
  supply in a no-network image smoke test. Missing cached tools fail immediately
  in hosted jobs rather than downloading over the runner's weak egress.
- Give the three-transport MCP conformance case a finite aggregate test budget
  without changing its per-operation timeouts or removing any behavior checks.
- Verify the published image manifest against the five locked inputs, then
  publish and inspect the repaired source and hosted jobs on each selected peer.

## Capabilities

No new or modified specification requirement. This refresh restores the
existing fail-closed CI supply contract for changed lock inputs. The
`skip_specs: true` metadata records why this Change has no specification delta.

## Impact

The existing CUE CI declaration, both generated Forge workflows, the CI
emulator image assertion, architecture regressions, the adopter quality test
and its locked fixture, the native tool supply and image build, and hosted CI
observations. No new Python/npm product dependency, command plane, credential
store, or release tag is introduced. Go becomes a locked verification tool.
