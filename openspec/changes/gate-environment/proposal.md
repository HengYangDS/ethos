# Proposal

## Why

A verdict must depend on its subject alone. Five times in three days a proof's verdict, or what
it examined, moved with something outside the subject. Each case was measured on the releasing
host or relayed by the session that met it:

- **The shell that launched it.** Gate children dropped `MISE_` variables and kept Mise's
  activation state, so a result depended on the launching shell. `mise-activation-isolation`
  fixed it in 0.2.0-beta.11.
- **The host's package cache.** A full proof of 2026-11-15 failed two gates on one cause: the
  behavior gate's offline locked sync found no wheel for one interpreter in the host's uv cache,
  which a cleaner had emptied the day before. It held a wheel for 103 of 121 locked packages. A
  governed repository's proof lost 17 admitted minutes after a wait of 60 to the same cause.
- **The launcher's path.** Two controlled runs of one command gate on one commit of a governed
  repository both passed. Launched from a shell with another package manager first on the path,
  the gate's environments bound that manager's interpreters; launched through the locked
  toolchain, they bound the locked ones. The verdict was the same and the subject was not.
- **Ignored files.** A governed product tagged a release with three failed hosted runs. A tracked
  test pinned a digest of a value that includes ignored build output, so the full proof passed
  only in the lane that held the build.
- **The holder.** DR-0029 records that a verdict is not yet free of its holder: the prover of a
  unit is its landing owner.

## What Changes

Candidates for this row's design, none decided:

- The proof checks the offline environment in its readiness tier, before it takes a host ticket,
  and the refusal names the locked sync that refills the cache; or the gate's environment input
  comes from the repository's own cache root.
- A command gate runs with the locked toolchain first; or the result states which toolchain
  supplied each executable; or the proof refuses an executable outside the locked toolchain.
- The proof contract says whether a gate's inputs are closed over tracked files.
- ETHOS's own gates that refuse on a measure get an invariance test: the verdict holds under
  changes that do not change the subject, such as where it starts, its order, its path and the
  clock. As a product check for governed repositories this is a new rule, and it waits for the
  rule row.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The gate runner, the environment a gate child receives and the proof's readiness tier. Each
measured case becomes a regression.

Owner: the release lead. Next action: converge the design with the five cases as its acceptance.
Read again: at the cut of 0.2.0-beta.13.
