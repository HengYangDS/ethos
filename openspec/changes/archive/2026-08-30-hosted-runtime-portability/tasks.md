## 1. Contract and RED

- [x] 1.1 Add a controlled Darwin bootstrap regression proving `apt-get` is not
  invoked when Linux `ldconfig` is unavailable.
- [x] 1.2 Add Node runtime resolution regressions for the installed POSIX layout
  and the Windows package-root executable layout.

## 2. Unique owner repair

- [x] 2.1 Make the shared bootstrap choose prerequisites by operating system and
  fail precisely when the selected host contract cannot be satisfied.
- [x] 2.2 Add one package-local Node/npm resolver under the existing CI toolchain
  owner and route every wheel-build consumer through it.
- [x] 2.3 Delete repeated platform path assembly without adding PATH fallback,
  compatibility state, or provider-inline logic.

## 3. Closure

- [x] 3.1 Pass strict OpenSpec validation, focused tests, shell lint, repository
  architecture checks, and affected tests.
