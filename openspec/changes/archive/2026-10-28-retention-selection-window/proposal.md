# Proposal

## Why

Host-store retention can retire an installation that a repository's `CURRENT` names. Retention
releases every recorded consumer whose selectors name the installation in neither `CURRENT` nor
`ROLLBACK`. A repository is in exactly that state between pinning an installation, which records it
as a consumer, and the selector write that names it, which follows within the same `ethos hook
install`, `ethos lane start` or `ethos adopt`. A retention that another repository's activation runs
inside that window unlinks the record. When the installation's last other consumer goes, the next
retention removes the installation. Every command in the first repository then fails: while the
deletion runs, `runtime/<digest>` exists without `manifest.json` and selection reports
`hook_runtime_manifest_invalid`; afterwards it reports `hook_runtime_current_target_invalid`.

- The race is platform-independent. A probe that calls `retire_unused_installations` on a private
  store reproduces it on macOS: the first retention drops the pinning repository's record, and the
  second removes the installation that the repository's `CURRENT` then names.
- Hosted Windows host conformance failed with `hook_runtime_manifest_invalid` on `56a56b802` (job
  122839601215, first-change lane) and on `a6ad56b67` (job 122884623884, first-change handoff). The
  installed-package acceptance runs formation beside brownfield and lifecycle activations on one host
  store, so it supplies both retentions, and NTFS removes `manifest.json` before the large `python/`
  tree, so the absence stays visible for seconds. Whether this interleaving caused those two jobs is
  not proven; it is the only mechanism found that produces the symptom.

The distribution specification already says that unknown liveness prevents deletion and that
reclamation keeps a live consumer's selected bytes. A repository between pin and selection is a
live consumer whose selection cannot be observed yet.

## What Changes

- A repository holds its runtime selection lock from the selector read before its pins until the
  selector writes that name what it pinned, in hook installation (which lane start and candidate
  projection use) and in adoption.
- Retention reads each consumer's selectors under a non-blocking acquisition of that consumer's
  selection lock. A held lock is unknown liveness, so the record and the installation stay.
- The selection lock becomes one object per repository common directory, so the selector effects
  inside such a selection re-enter it.
- A changelog entry under `[Unreleased]`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `distribution`: the requirement "Installed product migration preserves live consumers" counts a
  repository between pinning and selecting an installation as a live consumer.

## Impact

- Code: `src/ethos/adapters/repo/runtime/selection.py`,
  `src/ethos/adapters/repo/runtime/materialization/host_retention.py`,
  `src/ethos/adapters/repo/hook/activation.py` and `src/ethos/adapters/repo/adoption.py`; tests in
  `tests/unit/adapters/repo/runtime/materialization/test_host_retention.py`.
- A second selector effect in the same repository waits for a selection that pins supply, within the
  existing 10 s bound, instead of interleaving with it.
- Repositories that still run an earlier release keep the old window until they rebind.
- `python_product` grows by at most 8 lines.
