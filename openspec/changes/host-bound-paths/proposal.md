# Proposal

## Why

The owner directed on 2026-11-17, as relayed by the session that governs the fleet's
repositories, that neither ETHOS nor a governed repository hard-codes, with a hard-coded path as
the typical case. A census of the same day by that session read the accepted branch of this
repository and of thirteen governed trees, lock files excluded. Its counts are its own, except
where this text says otherwise:

- A host's home path or user name in tracked files: one research repository holds the path 204
  times and the name 296 times, most of them in evidence records, and two repositories hold one
  each. This repository's product, tool and configuration sources hold none: counted at this
  lane's head with `git grep` for the home, package-manager and Windows profile prefixes over
  `src`, `tools`, `system` and `.config`, 0 lines.
- A host tool or browser location written as a literal in product or tool code: three
  repositories. One sets a browser bundle's path in its pipeline model, the class that blocked
  an executed copy of that repository on 2026-11-16.
- Synthetic platform paths in test fixtures: three repositories, 142 in all. They test path
  handling and bind no host.
- One repository holds a guard that refuses host paths, which is correct by intent.

ETHOS enforces nothing for this class. Redaction covers peer identity and private addresses in
records, and no paradigm obligation or gate refuses a host-bound path in a tracked authored
file.

The class: a tracked authored file binds itself to one host's layout, such as a user home, a
package manager's prefix, an application bundle or a temporary directory, where it could resolve
that place on the destination through an environment variable, a declared tool or a
configuration key.

## What Changes

Candidates for the design, none decided:

- A structure rule reports a host-bound path in a tracked authored file, by the class of its
  prefix.
- The rule tells three cases apart, which the census met. An immutable record is reported or
  redacted and never rewritten. A synthetic path in a fixture is test data, so a declared
  placeholder form passes. A list of well-known install locations is resolution and no binding
  where an override exists.
- A tracked symbolic link whose target leaves the repository binds the tree to one host's
  layout in the same way and joins this rule, as the owner decided on 2026-11-17. A relative
  link that stays inside the repository does not. Counted on that day with Git's tree
  listing: the 31 governed checkouts on the releasing host track no symbolic link.
- A second class of host-bound literal joins only with measured cases of its own.

Under DR-0029 a new rule reports for one release before it refuses, and the law freeze admits no
new rule before 0.2.0. The owner decided on 2026-11-17 that the rule first reports in the first
batch of 0.3.0, so the freeze holds, and that it may refuse no earlier than the release after.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The structure rules and their report. In the release that first reports, each governed
repository reads its own count, and nothing is refused.

Owner: the release lead. Next action: converge the design on the census's three cases for the
first batch of 0.3.0. Read again: when the batches of 0.3.0 are planned.
