- [x] **1.** Admit the exact read-only transition row and terminal-v1 bytes.
- [x] **2.** Prove drift fails closed and installed readers pass.

| Evidence | Task | Command |
| --- | --- | --- |
| parser and projection | 1 | `pytest -q tests/unit/lanes/test_lane_family_profile.py` |
| package-only reader | 2 | `python -m nox -s install_smoke` |
