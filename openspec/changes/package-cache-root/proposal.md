# Proposal

## Why

The archived `rc-plan` design orders the row `gate-environment` in its Family 4 (lines 101 to
104, R8(c)), so that a proof's verdict depends on its subject. The Change `gate-environment` is
that row's first slice, in 0.2.0-beta.13, and its design (Decision 8) hands the package cache to
this Change: the cache is the one input of a proof that the host's other work can empty or fill.

Two things were measured:

- **A verdict moved with the cache.** A full proof of 2026-11-15 failed two gates on one cause:
  the behavior gate's offline locked sync found no wheel for one interpreter in the host's uv
  cache, which a cleaner had emptied the day before. A governed repository's proof lost 17
  admitted minutes after a wait of 60 to the same cause.
- **The cache grows without a bound.** Lanes, tests and proofs on a workstation build into the
  one uv cache that every repository of that host shares, while the hosted jobs use a cache root
  of their own. Read on 2026-11-17 with the bucket's directory names and `du`: 39 unpacked wheels
  of this product hold 12.3 of the 16.9 GiB in the archive bucket, about 324 MiB each, every one
  a distinct build installed from a path or URL. They stay referenced, so no pruning removes
  them. Which command writes them is not measured: runtime materialization sets `UV_NO_CACHE`,
  and the one wheel reference that a child receives without it is the observer requirement of a
  native attempt.

The owner asked for the root fix on 2026-11-16, as the session that keeps the host's supply
relayed, and decided its shape on 2026-11-17.

## What Changes

Decided by the owner on 2026-11-17, and built in 0.2.0-beta.14:

- One package cache root for each repository, under the Git common directory.

Designed here, around that decision. The page that the owner answered showed the root alone, with
the estimate below and the note that nothing is filled in advance:

- The product's own wheel is installed without the cache, and the behavior gate's offline sync
  runs in the readiness tier, before the host ticket. The study recommended both with the root.
- The root lies beside the native tool cache, and an explicit `UV_CACHE_DIR` still wins, as the
  hosted jobs set it.
- A proof fails until its repository's root is filled once by an online locked sync, and
  readiness names that sync. No wheel is copied into a lane, which is what the page's note meant;
  this one sync was not on the page.
- The first task measures which command writes the product's unpacked wheels.
- A dry run of the offline sync passes on an empty cache, so the readiness check is the real
  sync into the attempt's scratch.

Estimated at 90 product and 150 test line-equivalents, without a spike. Measured on 2026-11-17
with uv 0.13.8 on private caches, in three runs, for a lock of 121 wheel directories: an offline
sync from a filled root took 1.5 to 2.3 seconds, a repeat 0.03 seconds, and installing the
project without the cache 1.6 to 2.2 seconds, which left the cache unchanged.

Considered and not taken:

- **One root for each lane**, under the disposable tool supply that goes with the lane. Seeding
  it with the lock's wheels took 1.8 to 3.7 seconds and 686 MiB of apparent size. The lane's end
  bounds it, and where files cannot be cloned each lane costs those bytes.
- **The host's cache stays.** Nothing is built, and the first measured case returns with the
  next cleaner.
- **One store that is only read**, with builds beside it. uv refuses a store that it cannot
  write, and one whose buckets it cannot write, in three link modes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The Python behavior gate, the native attempt's observer requirement, the proof's readiness tier
and the generated-state topology. No part of `gate-environment` depends on this Change.

Owner: the release lead; the shape is the owner's decision of 2026-11-17. Next action: measure
which command writes the product's wheels, then design the root and its readiness check. Read
again: at the cut of 0.2.0-beta.14, which builds it.
