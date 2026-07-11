# Design

## Fixed Point

ETHOS remains a small repository-governance product with one truth boundary and
one lifecycle. Its implementation shape becomes declaration-first and functional
at the core:

```text
typed input -> pure compiler/reducer -> immutable typed projection -> adapter
```

Pydantic v2 supplies strict public contracts; nested mutable data is normalized
to frozen child models, tuples, or readonly boundaries. TOML supplies durable
registries and state-machine facts. CEL supplies only restricted predicates over
typed facts. Jinja renders typed projections under `StrictUndefined`. `graphlib`
is the only graph-ordering implementation.

## Compression Is A Product Invariant

The source budget counts all maintained executable carriers, including tests,
tools, declarations, templates, and tracked generated projections. It reports
both per-carrier and global values and is independently cross-checked by `scc`.
A migration is not complete until its replaced mechanism, dedicated tests,
compatibility shims, scripts, and duplicated declarations are deleted.

Temporary growth is explicit compression debt. Each record must identify the
added surface, replacement, owner, expiry, deletion wave, and expected net
deletion. There is no baseline reset or silent debt extension.

## Quality And Carrier Admission

Format selection becomes fail-closed. Every carrier has a native formatter or
an explicit output/renderer canonicalization exception, parser, semantic owner,
behavior proof, cache home, supply-chain owner, and gate. Python and Node tools
are repository-locked dependencies, not host assumptions. The selected quality
set deliberately avoids overlapping default gates and preserves one owner script
per concern.

## Provider Boundary

`act --list` and `gitlab-ci-local --list` are discovery operations only. A local
provider verdict records an actual selected formal workflow/job execution,
container mapping, exact HEAD, versions, and result. Unsupported hosted-only
steps remain explicitly hosted-observation-only. Local success cannot promote to
a hosted CI or publication claim.

## Migration Safety

Each vertical slice uses a bounded old/new parity corpus before cutover. CEL is
limited to predicates; no lifecycle mutation, IO, dynamic import, or arbitrary
Python function enters the CEL environment. State-machine, command-registry,
and read-model declarations compile into pure functions; adapters retain IO.

Property tests cover laws and state spaces that would otherwise require repeated
example tests. Mutation testing is nightly and limited to pure reducers and CEL
compiler/adapters. Tests may be deleted only with unchanged behavior contracts
and non-regressing coverage/mutation evidence.

## Rollback

Each wave is independently reversible until old code deletion. A failed parity,
source budget, or carrier admission gate blocks cutover and keeps the old path as
the current owner. After destructive deletion, restoration is a new governed
change from Git history; compatibility residue is not retained as an implicit
rollback mechanism.
