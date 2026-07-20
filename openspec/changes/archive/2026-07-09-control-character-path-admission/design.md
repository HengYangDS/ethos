# Design

The smallest correct boundary is the admission path token itself. ETHOS should
not resolve, normalize, join, display, or pass through a token that contains
control characters, because doing so can make one supplied token look like
multiple repository facts.

`prewrite_guard` therefore checks `Path.as_posix()` before root joining or
`Path.resolve()`. A rejected token reports:

- `path`: the original token;
- `relative_path`: empty, because no repository-relative fact was admitted;
- `ignored`: false;
- `tracked_candidate`: false;
- `allowed`: false;
- `reason`: `path_invalid_control_character`.

`hook_admission_report` preserves such tokens as tokens instead of joining them
to the target root. This lets the pre-tool result expose the exact malformed
input and return the specific `prewrite_path_invalid_control_character` gap.

The design follows the existing kernel: the change only refines Evidence and
Claim admission for target paths. It reveals a hidden state, calibrates the path
boundary, and keeps the transition loop centered without adding a new entity.
