## 1. Establish the failing boundary

- [x] 1.1 Preserve the accepted GitHub exact-HEAD logs for Windows Python 3.12,
  3.13, and 3.14 showing the same
  `hook_runtime_entrypoint_missing` isolated-wheel failure.
- [x] 1.2 Add a focused RED proving a Windows standalone image keeps
  `python.exe` at the interpreter root and selects `Scripts/ethos.exe`.

## 2. Restore native runtime layout

- [x] 2.1 Make runtime Python, scripts-directory, and entrypoint resolution
  share one platform-native layout owner.
- [x] 2.2 Preserve the Windows standalone interpreter root when copying Python,
  `Lib`, `DLLs`, and native runtime libraries.
- [x] 2.3 Delete the old `Scripts/python.exe` assumption and avoid fallback or
  compatibility launchers.

## 3. Verify semantic closure

- [x] 3.1 Prove focused runtime selection, image materialization, generation
  finalization, and isolated-wheel smoke behavior.
- [x] 3.2 Run repository-wide reference closure, Ruff, format, module-layout,
  and the smallest affected quality gates.
- [x] 3.3 Complete exact-HEAD full proof before the official archive transition.
