## Design

The repair is test-only and intentionally local. The cross-host handoff test
will execute `git bundle verify` directly with `LANG=C` and `LC_ALL=C`, leaving
the surrounding pytest process and every shared helper unchanged. A successful
Git exit remains mandatory, and the deterministic output continues to prove
that the bundle records a complete history.

This is narrower than forcing the entire test suite into one locale and stronger
than replacing the message assertion with only a ref listing. No production
code path is changed.

## Risks and rollback

The C locale could expose a platform-specific Git wording change. The command's
zero exit still provides the primary validity check, while the phrase retains
the current complete-history contract. Revert the single test change if Git's
stable C-locale contract changes, then replace it through a separately reviewed
machine-readable verification mechanism.
