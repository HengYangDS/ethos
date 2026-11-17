# Proposal

## Why

The owner asked on 2026-11-17, as relayed by the session that publishes this product's
architecture book, whether the command surface's source is organised by meaning, and then asked
for a systematic, mechanised answer to how source is organised. The case: `surface/cli` holds
five modules beside one package, `root/`, whose only module is the MCP launcher of 17 lines.
That package held one module for each root command until three Changes of 2026-11-08 to
2026-11-11 moved the commands into the operation catalog, and the package stayed. The module
layout rule's own text names the launcher's path, so the rule holds the leftover in place.
Beside the package stands `root_binding.py`, where "root" means the repository's root and not
the command tree's.

It is one case of a class. Counted at this lane's code head from Git's own listing of
`src/ethos`, 406 modules in 86 packages:

- 26 packages hold one module and no package, and 24 of them stand beside modules of their
  parent, so one level mixes modules and packages;
- 20 packages hold both modules and packages, the widest with 29 modules beside 9 packages;
- 4 modules share their first word with a sibling package.

The relaying session's own scan adds two measures that this text does not repeat: 4 modules
whose importers all lie in one package below them, and 55 modules with exactly one importer, in
another package.

What decides a package's shape today is prose. The module layout rule orders four decisions for
a package that looks redundant: delete, collapse, retain, split. It says that a retained
package's boundary must be visible in its consumers or in the packaging or runtime contract,
and that counts are evidence for review and never the rule. The module layout gate measures
names, facades, imports, empty packages and command owners, and nothing of a package's shape.
The structure design that the owner approved on 2026-11-14 counts one-module packages and
leaves the decision to that prose. So a retained one-module package records nowhere which
boundary it owns, a deliberate boundary and a leftover look alike, and a Change that empties a
package passes its proof.

## What Changes

Candidates for the design, none decided, as the relaying session gave them:

- A one-module package passes where a boundary can be observed from the tree: a registration or
  an entry-point target, the adapter of a named external framework, or one of an axis whose
  siblings are all packages. Otherwise the gate reports it, in the proof of the Change that
  leaves it so. The boundary is derived and never listed.
- Among siblings one word has one meaning.
- A module lives in the lowest package that holds all its importers.
- Existing stock is held by a count that never rises, and by no list of exemptions.
- The rule's text names no concrete path that the gate could derive.

To settle in the design: which of these is a measure that holds under changes that do not change
the subject, and which stays a judgment that a review makes with the measure before it; how each
reads a repository of another language; and how the rule joins the structure design's report,
whose third rule already counts the same packages.

For governed repositories this is a new rule. The law freeze admits none before 0.2.0, and a new
rule reports for one release before it refuses. The moves in this repository's own tree, the
command surface's first, are the structure design's own-tree step and need no new rule.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The module layout rule, its gate and the structure report. The design is studied first on this
repository's own tree.

Owner: the release lead. Next action: a design study that measures each candidate on this
repository and on the governed repositories that the releasing host reads. Read again: when the
batches of 0.3.0 are planned, with the structure report.
