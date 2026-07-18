# Design

The repair stays inside the existing CI template owner script and architecture
contract tests:

- `tools/ci/ci_templates.py` remains the single owner for CI template and local
  emulator evidence behavior.
- Observation modes are explicit through `_mode_is_observation` and
  `_emulator_tool_required`.
- Missing provider tools in observation mode produce non-claim local evidence
  with `ok=true`, `tool_available=false`, `returncode=127`, and hosted status
  booleans false.
- Missing provider tools in materializing run mode still produce `ok=false` and
  return 127.
- Tests load the owner script from its repository path instead of depending on
  importability of `tools.ci`, keeping `tools/ci` a script owner surface rather
  than a product Python package.

This does not add a new provider ontology or weaken hosted CI: hosted CI still
runs the owner scripts, local emulator evidence still cannot claim hosted status,
and real provider materialization remains fail-closed.
