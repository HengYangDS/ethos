## 1. Package authority

- [x] 1.1 Update the exact package declaration to `@fission-ai/openspec@1.9.0`.
- [x] 1.2 Regenerate the npm lockfile from the official npm registry and verify version, URL, and integrity.

## 2. Current contract closure

- [x] 2.1 Update current governance specification and runner documentation from 1.8.0 to 1.9.0.
- [x] 2.2 Update the archive-transition contract expectation to 1.9.0.
- [x] 2.3 Confirm archived historical records remain unchanged.

## 3. Verification and closeout

- [x] 3.1 Run `npm ci` with the locked dependency.
- [x] 3.2 Run OpenSpec 1.9 strict validation and doctor.
- [x] 3.3 Run the focused archive-transition contract test.
- [ ] 3.4 Archive this Change through the governed lifecycle with the resulting evidence.
