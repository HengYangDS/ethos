## Why

The complete proof audits uv.lock but omits package-lock.json. The accepted npm
lock contains a high-severity vulnerable transitive TOML parser despite a green
Python security gate. Missing input coverage is a quality-owner defect, not an
adopter responsibility or a reason to suppress the alert.

## What Changes

- Replace the Python-only audit module and gate label with one dependency-audit
  owner that invokes uv and npm through the locked toolchain.
- Bind native results to exact source, both manifests/locks and audit policy;
  reject timeout, missing output, malformed output and concurrent input drift.
- Use npm native override resolution for the patched stable parser while the
  direct Markdown tool pins the affected version. Retire the override once the
  direct dependency supplies an acceptable current parser without it.
- Preserve separate raw observations and one aggregate verdict; move failures
  before package delivery while keeping offline tests independent without a second CI lifecycle.

## Capabilities

### Modified Capabilities

- `quality`: dependency security covers both declared lock ecosystems and fails
  closed at observation and freshness boundaries.

## Impact

Existing quality-gate governance, native audit policy, Python/Nox adapter,
package declarations/lock, focused tests and the canonical terminal plan.
No adopter mutation, new lane, new runtime framework, global dependency upgrade,
proposal lifecycle implementation or unrelated structural rewrite.
