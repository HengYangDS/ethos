# Proposal

## Why

The archived `rc-plan` design names this row in Family 3 (lines 92-95): "proofs write gate evidence
and artifacts to owned scratch or their owner stores within D's byte budgets, and adopter gates
keep their environment and bytecode in the attempt's scratch". Appendix E.2, item 10 (lines
774-776) gives the adopter half its first form: a declared command gets `UV_PROJECT_ENVIRONMENT`
and `PYTHONPYCACHEPREFIX` in the attempt's scratch, with exceptions for `ty` and the Node supply.
The plan's decision 5, item 3 (lines 206-208) makes it one of the two halves of lane residue, the
other being `residue-class`. The committee's resolution of 2026-11-14 places the row in
0.2.0-beta.13, and the release-candidate gate asks that lanes stop holding gate evidence
(`docs/decisions/dr-0026-release-candidate-gate.md`).

The study of `residue-class` held that row until this one has a design: a landed lane retires
without a content review only when everything it holds beside tracked files is a declared, checked
root, and the lane reviews that its study counted also held evidence files. The design of
`host-reservation-guests` hands two things here: the owner mark for the scratch that its decision
9 does not reach, and the one root that its decision 11 needs before a dead owner's scratch can be
released.

What the code shows at the base:

- A provider gate already writes nothing into a lane. Its scratch is a directory under the
  temporary root, and its evidence goes to the Git-common store. Six calls under
  `src/ethos/adapters/gates` each make such a directory by themselves, and one of them is marked
  with its owner.
- A declared command runs in the lane with the environment of its launch. Where it writes is
  decided by its own configuration. In the tracked declarations of 16 governed profiles, 8 declare
  gates: 25 commands and 9 providers. Of the 25 commands, 3 declare native outputs and 1 names a
  `build/` path in its arguments (counted from the tracked `.ethos/*.toml` files of one checkout of
  each profile). For the other 21 the declaration does not show where the command writes.
- ETHOS's own registry, `system/repository-gates.toml`, holds 16 declared commands
  (`grep -c "^command = "` over it). Their sessions name a path under `build/` in 25 lines of 10
  files (`grep -rn '"build/' tools/ci`): 11 an evidence home, 7 an artifact home and 7 a runtime
  home. 8 upload steps of the pipeline model read such paths from hosted jobs that run the
  sessions directly.

## What Changes

- A declared command may name the scratch directory of its run of gates with `{scratch}` in its
  arguments, beside the placeholders `{python}` and `{native_output}`. The directory lies under
  the temporary root, in a root that is made when a command first names it, marked with its
  owner's record and removed when the run ends. A command that does not name it receives what it
  received before.
- The product's own probes make their scratch inside the same root (tasks 1.2 and 1.3).
- A proof that executes its gates, full or focused, reports what its attempt left in the lane:
  the files and bytes that appeared or changed under the evidence and artifact homes of the
  artifact topology, the new names under the work home and each new nontracked root. The report
  changes no verdict, exit or required gap.
- Evidence that must outlive an attempt stays what it is today: a declared native output, kept in
  the store's `artifacts` and retired by the retention verb under its byte budget.

Not breaking. No gate that exists receives another environment, argument or working directory, and
no tree or invocation is refused.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: two new requirements, `A declared command names the scratch of its run` and
  `A proof reports what its attempt left in the lane`. Tasks 1.2 and 1.3, the probes' move into
  the run's root, add no requirement to this delta.

## Impact

- `src/ethos/adapters/gates`: two new modules, for the scratch and for the footprint; the
  runner's launch of a declared command; the capture and the custody check of native evidence;
  for tasks 1.2 and 1.3 the six scratch makers. `src/ethos/application/proof/operation.py`: two
  calls for the report. The gate runner page and the changelog.
- Size, measured by the budget tool on each patch: 40.9 product and 147.2 test line-equivalents
  for the placeholder with its root, 119.4 and 119.1 for the report. Tasks 1.2 and 1.3 are not
  measured: estimated at 45 product and 90 test line-equivalents.
- Not here: the move of ETHOS's own sessions and registry to `{scratch}`, which needs a release
  that reads the placeholder first; the release of a scratch root whose owner is gone; the two
  variables of the plan's item 10, which are the owner's decision; `residue-class`.
