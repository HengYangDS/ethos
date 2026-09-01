## 1. Establish the exact failing boundary

- [x] 1.1 Preserve exact accepted-HEAD hosted evidence that Windows Python 3.12,
  3.13, and 3.14 pass interpreter relocation and fail only at
  `Scripts/ethos.exe --version` with `hook_runtime_entrypoint_smoke_failed`.
- [x] 1.2 Add focused RED tests requiring immutable-runtime commands and smoke
  to execute `<runtime-python> -B -I -m ethos.cli`, and requiring runtime
  finalization not to depend on a generated ETHOS launcher.

## 2. Converge execution authority

- [x] 2.1 Remove console-launcher identity from `SelectedRuntime` and route
  `runtime_command()` through the selected Python module.
- [x] 2.2 Make materialization finalization and smoke require only the owned
  interpreter plus authenticated package files, route locked uv discovery
  through that interpreter's module boundary, and preserve exact subprocess
  diagnostics on failure.
- [x] 2.3 Update the isolated-wheel package-only smoke and delete stale launcher
  assumptions from tests and terminal documentation.
- [x] 2.4 Prove repository-wide reference closure and focused runtime, hook, and
  isolated-wheel GREEN.

## 3. Complete the active Change

- [x] 3.1 Complete exact-HEAD full proof for the final pre-archive source and
  official Change artifacts.

## Post-archive transition boundary

Official archive creates a distinct signed HEAD. That exact archive HEAD still
requires reproof, candidate and accepted CAS, fresh immutable-runtime activation
and readback, exact publication to every declared Forge, and hosted Windows
Python 3.12, 3.13, and 3.14 evidence. Related Windows lanes remain live until
those post-archive observations prove absorption.
