## Why

The accepted Windows runtime layout now preserves the native standalone Python
tree, but GitHub Windows Python 3.12, 3.13, and 3.14 still reject the generated
runtime because post-observation compares Windows path spellings as raw text.
The interpreter reports native backslashes while the expected path is rendered
with forward slashes, so one path is misclassified as two and hosted acceptance
remains open at `hook_runtime_python_not_relocatable`.

## What Changes

- Compare observed and expected runtime prefixes by platform-native path
  identity rather than serialized spelling.
- Preserve the existing native relationship among `python.exe`, `Lib`, `DLLs`,
  runtime DLLs, and `Scripts/ethos.exe`.
- Add a focused regression for equivalent Windows slash and case forms and keep
  generation post-observation as the executable proof.
- Delete raw-string path equality; add no launcher, fallback lookup,
  environment override, or second runtime layout.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `runtime-activation`: Runtime post-observation compares Python prefixes using
  platform-native path identity before activation.

## Impact

- Windows Python image construction and runtime-generation post-observation
  under `src/ethos/adapters/repo/runtime/materialization/`.
- Focused materialization tests and the existing isolated-wheel hosted smoke.
- The existing terminal convergence plan records the corrected native path
  identity boundary and its hosted acceptance requirement.
- GitLab identity-drop/process-spawn, tempfile governance, and repository-wide
  module or documentation topology remain separate successors.
