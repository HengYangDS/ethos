# Proposal

## Why

`shared-quality-obligations` made ETHOS consume the obligations it ships for every repository and
landed on `dev` at `6186a48c4`. Its first hosted run, 40796064834, failed two jobs whose gates had
passed in the lane's local proof:

1. **external link health.** `prove --host --execute --gate external-links` refused to execute with
   `quality_obligation_unproven:behavior` and `quality_obligation_unproven:static-analysis`. A
   focused selection counts as a code check when any input of a selected gate is a code subject. In
   ETHOS a gate's provider module is such an input, because a tree that builds the product supplies
   its own providers. The obligations of the same selection thus depend on where a gate's
   implementation lives, which "ETHOS is judged as every repository is" excludes. Focused
   `docstrings` and `shell-lint` refuse the same way.
2. **quality gates.** The hosted proof stopped after 18 seconds with `process_cancelled` and no gate
   result. The new `code-static` gate resolves the repository's mise-declared Node with
   `mise which node`. The hosted job installs cue, actionlint and Go through mise but supplies Node
   only through ETHOS's own tool cache, so the provider fails with
   `mise_supply_unavailable:node`. The provider reports that failure, but the failure first left a
   nested `command_scope`. Every nested scope shares the proof's one `CommandScope`, so the failure
   cancelled it, and every sibling gate's next command failed with `process_cancelled`.

A local run that prepares a fresh mise data directory as the hosted job does reproduces both steps
of the second failure.

## What Changes

- **Focused obligations follow what the selected gates verify.** A focused selection compiles code
  obligations only when a selected gate verifies a code-correctness axis or declares a quality
  dimension. The selected gates' inputs still select the source contracts whose members they read.
- **A nested command scope owns its cancellation.** Each `command_scope` owns the commands started
  under it. A failure that leaves a nested scope cancels only those commands; cancelling an
  enclosing scope still reaches every nested scope, and a cancelled scope still refuses new
  commands.
- **CI installs the declared Node through mise.** CI preparation installs Node with cue, actionlint
  and Go from the locked mise selection that development uses. An immutable supply image without
  it fails preparation and names Node.
- **CHANGELOG.** One entry under `[Unreleased]`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: a focused check that verifies no code property compiles no code obligation; a failure
  reported from a nested command scope stays within it; CI resolves a declared tool on a clean
  runner from the same mise selection as development.

## Impact

- Python product code stays within its 70,000-line ceiling; `design.md` records the measurement.
- Hosted CI: the quality job installs Node through mise as well as into ETHOS's tool cache. The
  GitLab supply image needs a rebuild that includes mise's Node before its offline preparation
  passes; its supply manifest is already stale and owned by the supply work.
- Governed repositories: a focused diagnostic whose gates run repository scripts no longer
  requires the code floor. Default and full proof are unchanged.
