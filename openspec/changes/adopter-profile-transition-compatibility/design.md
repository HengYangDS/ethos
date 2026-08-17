# Design

The loose role reader accepts only the exact deployed row and discards it. The
strict parser remains closed. `plan` reuses terminal-v1 byte identity, marks
proof and mutation authority false, and emits no v2 plan. One installed-wheel
fixture proves `status` and `plan`; no general v1 model or executor returns.
