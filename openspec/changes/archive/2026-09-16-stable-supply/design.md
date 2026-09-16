## Selection

Official registry observations and upstream releases identify filelock 3.32.7
and virtualenv 21.7.10 as non-yanked, non-prerelease updates. A native uv lock
dry-run, retaining the existing ty and mutmut selections, selects only these
two changes. The former updates locking support; the latter fixes environment
activation and configuration handling. Neither requires a new product model.

`pyproject.toml` continues to own direct requirements and `uv.lock` the resolved
closure. Do not promote virtualenv into a direct requirement or introduce a
second version inventory. Keep `prerelease = "disallow"`. Publisher maturity
and release version syntax remain distinct observations; this Change grants
no preview exception.

## Boundaries

The latest nodejs-wheel-binaries package still embeds Node 24.19.0 and npm
11.17.0. Current official Node releases and npm's release tag are separate
upstream facts, not evidence that the installed payload has changed. Their
runtime supply repair remains a separate bounded closure in the existing plan.
The Architecture adopter's pending merge remains owned by its task; dependency
verification does not authorize touching its refs, index or coordination state.

## Verification And Recovery

First inspect the exact native lock diff and synchronize the owned environment.
Run existing lock/materializer, runtime-selection and audit regressions, static
owners and official OpenSpec validation before freezing the signed candidate.
Then obtain exact full proof, including package execution, official archive and
accepted runtime readback through the current public decisions. Keep source,
installed runtime and remote publication claims separate.

A failed candidate leaves the installed predecessor selected. Any rollback is
an admitted source/lock transition followed by native synchronization; never
edit installed immutable dependency bytes or copy a previous proof verdict.
