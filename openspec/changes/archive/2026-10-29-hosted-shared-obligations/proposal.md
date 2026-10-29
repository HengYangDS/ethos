# Proposal

## Why

`shared-quality-obligations` landed on `dev` at `6186a48c4`, and hosted run 40796064834 failed two
jobs whose gates had passed in the lane's proof. A focused `external-links` refused to run because
a selected gate's own implementation, which ETHOS's tree supplies, counted as a selected code
subject, so the same selection obliged ETHOS differently from any other repository. On a clean
runner the new `code-static` gate found no mise-installed Node. Its reported failure left a nested
command scope and cancelled the proof's shared scope, so every sibling gate stopped with
`process_cancelled`. A local run that prepares a fresh mise data directory as the hosted job does
reproduces both failures; `design.md` traces their causes.

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
