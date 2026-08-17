- [x] **1. Select publication proof by repository authority.** Load the exact
  accepted-HEAD repository Commitment and use the existing authority-specific
  resolver without weakening generic proof semantics.
- [x] **2. Install the locked source runtime closure.** Make source-built hook
  runtime installation consume `uv.lock` offline with no ad hoc pin or fallback.
- [x] **3. Prove implementation closure.** Run focused and full publication and
  runtime test files, strict OpenSpec validation, Ruff, and diff checks. Full
  lifecycle proof, adopter probes, and remote publication follow this task atom.

| Evidence | Tasks | Command |
| --- | ---: | --- |
| publication authority | 1 | `pytest -q tests/unit/cli/land/test_publication.py` |
| locked runtime | 2 | `pytest -q tests/unit/cli/test_hook_runtime.py` |
| declared model | 3 | `openspec validate model-promotion-forward-fix --strict --no-interactive` |
