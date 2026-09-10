## Context

Projection implementation full proof passed 35 gates. Its archive proof then
failed ten tests and one setup, all at the same ten-second hook-contract query.
A separate eight-worker replay passed 103 tests; injected timeout still escaped
as `TimeoutExpired`. Import tracing shows the pure launcher query importing
runtime authority, repository profiles, Pydantic and file-lock machinery.

Two version-identity tests reproducibly fail at offline Hatchling installation.
The same unchanged tests pass when using the installed locked build environment,
which is already the production delivery contract. Ambient cache contents must
not decide these tests' behavior.

## Goals / Non-Goals

- Reduce the query's dependency closure and retain exact failure evidence.
- Preserve immutable package ownership, launcher bytes, deadline and fail-closed
  admission; never infer permission from a cached or guessed launcher.
- Reuse locked build supply for package identity tests.
- Do not tune global concurrency, weaken proof, add a cache or modify diagrams.

## Decisions

Keep the existing binding query protocol so a source reader can still query the
currently installed older package. Pure launcher projection remains in its
existing owner. Runtime/authority observation moves into a concrete observation
module with its callers; pure executable layout belongs to the existing filesystem
owner. This removes incidental import-time work without adding a second
implementation. The initially tried local-import deferral was replaced by this
semantic split, retaining the native top-level import rule without suppression.

Catch deadline expiration at the hook observation boundary. Preserve binary,
argv, cwd, deadline, captured stdout/stderr and the fact that this was a read-only
query. Admission stays unarmed; the next action is fresh observation rather than
an unnecessary runtime reinstall. Malformed contracts keep their existing
repair behavior. Do not make retries implicit.

Package tests select their executing locked interpreter and use its installed
build dependencies with isolation disabled, exactly as delivery does. Empty
cache execution proves the distinction; missing locked dependencies still fail.

## Verification

First fail regressions for public timeout projection and a cold child whose
import set contains no runtime authority, selector or third-party validators.
Preserve exact launcher output and Windows layout tests. Run package identity
checks with an empty cache and without ambient override flags, focused hook and
runtime tests, then normal exact full proof and archive/acceptance.
