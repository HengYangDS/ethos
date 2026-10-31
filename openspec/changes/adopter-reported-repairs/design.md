# Design

## Context

The release builder lays out the Windows, macOS and Linux archives as `ethos/bin` for the consoles
and `ethos/runtime/<runtime digest>/` for the materialized runtime
(`tools/ci/delivery/distribution.py`). The Windows console runs
`..\runtime\<digest>\python\python.exe`. Mise installs the archive under its data directory, and a
governed repository may place that directory inside the job's build directory. The host store
already names its directories with the first 16 hexadecimal digits of a digest
(`src/ethos/adapters/repo/runtime/materialization/effect.py`), and the runtime digest and manifest
are computed from paths relative to the runtime directory, so the directory name is not part of
either.

Archive compensation (`src/ethos/adapters/mutation/lane_lifecycle/archive/compensation.py`) checks
the Lease, the attested archive and the candidate branch, not publications. Every publication
records a `publication:remote-effect` Attestation with each peer, target ref and desired object, and
`latest_publications` in `src/ethos/adapters/repo/attestation_lifetime.py` already selects each
peer's latest publication of each ref.

A repository's format-selection increment (`.config/checks/format-selection/policy.toml`) may
declare only byte-bound carriers: `format_owner = "immutable-carrier"`,
`mutation_policy = "forbidden"`, explicit paths and a validation owner among the repository's full
proof gates. The paradigm report measures every tracked registry-language file except received
paths, the files Git attributes mark vendored or generated.

## Goals / Non-Goals

**Goals:**

- A governed repository can run ETHOS on Windows under a deep install root.
- Compensation never orphans a published proposal.
- A frozen record stays exactly as its evidence binds it, while every mutable code file keeps the
  ceiling.

**Non-Goals:**

- Enabling long paths on Windows hosts, which remains the host's configuration.
- Changing the host store layout, selectors or rollback.
- Exempting any file whose bytes may still change, or any path by name.

## Decisions

1. **The archive keeps its depth and shortens the digest.** The runtime directory is named with the
   first 16 hexadecimal digits of the runtime digest, as the host store already does. An archive
   carrier accepts the full digest or its prefix and returns the full digest from the manifest; the
   host store and its selectors stay strict. Dropping the digest level was rejected: the wheel
   lookup and the runtime's recognition of its own interpreter path rely on it, and a second layout
   would spread through four product modules. A fixed literal name was rejected because it loses the
   identity check. A path-budget test keeps the archive-relative Windows interpreter path within 64
   characters, which leaves an install root of up to 172 characters below the 236 that the guest
   measured.
2. **Compensation reads the publication record, not the peers.** The guard asks whether a peer's
   latest recorded publication of any ref selects the archived head. It needs no network, so a
   compensation still refuses or proceeds deterministically, and the next action names
   `ethos publish --retire` for the selecting ref while the Work Lane still retains the head.
3. **Only proven byte-bound carriers leave the code ceiling.** The paradigm receives the paths that
   the repository's validated carrier declarations select, and the code ceiling skips them as it
   skips received paths. The declarations are read with the same validation the format gate uses,
   including the proof-gate check of the validation owner; any invalid increment yields no exemption
   and the format gate reports it. Names and every other obligation still apply.

## Risks / Trade-offs

- An alpha.23 console cannot select an alpha.24 archive through `--runtime`; it refuses without an
  effect. Upgrade and rollback between installed versions are unaffected.
- After the interpreter starts, Python still opens modules below the runtime directory. Under the
  157-character root above, the deepest product modules exceed 259 characters, so such a host also
  needs long paths enabled, which Python honours; that is host configuration, not a product change.
- A publication made outside ETHOS leaves no record, so the guard cannot see it.
- The product source budget had 62 effective lines of headroom before this Change; the additions
  stay within it or are offset in the same modules.
