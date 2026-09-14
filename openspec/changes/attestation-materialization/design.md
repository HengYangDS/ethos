## Context

The accepted implementation invokes hash-object and update-index for each set
member. It revalidates every canonical member on each selection. Existing native
batch evidence preserves identical trees while reducing 64-member construction
from 129 Git invocations to three; that isolated experiment is not shipped proof.

## Decision

Keep the existing attestation_set owner and exact public interfaces. Use one
owned temporary directory under the Git common directory for raw blob inputs
and an isolated index. Seed that index from the freshly observed set tree and
materialize only incoming members. Run hash-object --stdin-paths from the common
directory with relative, generated ASCII paths, avoiding assumptions about
workspace quoting or Unicode. Feed exact mode/object/path entries to native
update-index --index-info and write the tree. Git owns object hashing, object
format and index construction.

Use Python functools.lru_cache for successful pure canonical member validation,
keyed by complete bytes, with at most 2048 entries. Members larger than 64 KiB
are validated normally without retention. This bounds retained input bytes to
128 MiB; parsed-object overhead is additional and must be measured. Process
exit releases all entries. The cache has no disk representation or authority.

Every read still observes the current set ref, canonical root, tree entries,
blob framing and raw bytes. Ref selection, member paths, predicate selection,
policy, signatures, validity and effect-time admission are never cached. Failed
validation never becomes a cache entry. Reader failure after warm validation
still fails closed. A cache miss, eviction or oversized member changes work,
not acceptance. The implementation remains package-bound in one process.

A losing writer reobserves and recomputes the union before exact CAS. Native
batch failure cannot move the selected ref or change the caller's index. Owned
staging disappears on normal and exception exits; crash reclamation remains a
separate existing resource obligation, not a claim made by this refactor.

## Alternatives

- Caching a selected root or admission report would conflate immutable meaning
  with current selection and authority; reject it.
- A new persistent database or general cache engine adds a second lifecycle and
  maintenance surface; reject it.
- Raising timeouts or worker count preserves repeated work; reject it.
- Native batch construction plus standard-library pure-value reuse replaces
  current machinery without changing the set carrier or adding dependencies.

## Verification

First reproduce member-linear Git command growth and repeated canonical
validation through public set readers/writers. Preserve independent native tree
and raw-byte expectations, index isolation, SHA-1/SHA-256, insertion order,
concurrent union, single-witness selection and exception cleanup. Warm, cold,
evicted, oversized, malformed and changed-member reads must agree on meaning.
Exercise existing proof and publication consumers, then measure equivalent
workloads before freezing the exact source for full proof and delivery.
