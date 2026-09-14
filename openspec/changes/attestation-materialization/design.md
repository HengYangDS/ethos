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

## Full-Proof Counterexample And Bounded Repair

The first frozen proof at 6248ff72 completed with six failures, all from generic
fixture hook-contract queries reaching the ten-second deadline. Coverage measured
95.0994 percent; downstream proof gates were blocked by the failed suite, not
independent defects. Twelve isolated native starts retained exact prefix and
contract output, with only the first startup near one second; they did not
reproduce or explain every prior ten-second wait. No timeout increase or blind
full-suite retry follows from that observation.

The semantic defect is repeatedly executing a pure declaration whose data is
already part of the package. The source-equality shortcut was rejected during
review: a pair of equal source leaves does not prove a full import environment
or executing module meaning. Remove that uncommitted path entirely.

Move the launcher template, hook names and platform-relative Python paths from
Python literals into the package-adjacent binding.toml. The existing binding
owner strictly validates and renders this one declaration; both activation and
the selected-runtime observer consume it. Runtime inventory binds the declaration
with all other package bytes. Missing data requests a new runtime installation;
unreadable or malformed selected data leaves admission unarmed. The old child
query, timeout transport and duplicate launcher literals are removed, not kept as
a compatibility path. Actual hook execution still uses the selected interpreter.

The declaration is a package resource, not a new user configuration or runtime
state store. It replaces the existing literal owner and has no independent
version counter. A pre-migration package must be upgraded by the native package
activation sequence; the immutable installed package is never edited in place.
Package-only acceptance must cover the first upgrade and complete launcher
byte-equivalence, not only source tests.

Generic fixtures include the exact declaration in their minimal inventory.
Native regressions preserve declared bytes, missing transports, unreadable and
malformed data, symlinks, changed selected resources and failed activation
rollback. The first failed full proof remains preserved; exact source proof and
installed-runtime delivery remain open. No deadline or concurrency is increased.

The activation boundary carries a declaration read failure through compensation
with its original state, path and cause. The CLI projects that observation and
requests fresh status rather than disguising it as a process failure or deriving
an implicit reinstall. Successful rollback does not turn failed observation into
currentness or erase its evidence.

## Uniform File-Size Acceptance

The user's September 15 correction makes the repository's per-file ceiling
uniform. Keep the sole default in .ethos/rules.toml and remove test/surface
overrides; the generic policy compiler still honors other adopters' declarations.
The public gate must accept the exact ceiling and reject one additional effective
line for each role. Existing role labels remain descriptive, not extra capacity.

Nineteen current test files exceed that ceiling; no product file does. Consolidate
duplicated setup and independently changing obligations at existing test owners,
introducing a semantic module only where none already carries that responsibility.
Preserve parameter cases, assertions, collection and failure observations. Do not
minify code, change the counter or split by line ranges. The threshold correction
is a prerequisite to accepting this batch, not a reason to report the old floor
as current or to start another lane.

The concrete ownership changes are native test execution out of release assets,
runtime retirement out of hook activation, launcher generation apart from runtime
activation, source-resolution repair apart from valid resolution, proof admission
apart from issuance, receipt identity apart from retirement effects, and missing
Lease reacquisition apart from storage CAS. Delivery and source-budget tests use
semantic subpackages rather than new suffix series. Existing support owners are
reused; dedicated proof, signing and budget constructors replace inline copies.
Stable case values and their hashes survive relocation, with their current
source paths and consumers updated together.
