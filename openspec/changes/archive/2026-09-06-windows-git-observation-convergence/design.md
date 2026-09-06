## Context

See proposal.md for motivation. Package acceptance creates a generated adopter
whose ordinary tracked text is currently normalized according to the Git
configuration active during repository construction. ETHOS later observes that
repository through its isolated Git boundary, which intentionally excludes
ambient global and system configuration. On Windows, a global
`core.autocrlf=true` can therefore make the construction and observation phases
assign different semantics to the same bytes.

The existing `proof-hosts` specification already requires host-conformance
fixtures to declare complete repository-local Git semantics. The missing owner
is the generated adopter's tracked `.gitattributes`, not the production Git
observer or dirty-admission policy.

## Goals / Non-Goals

**Goals:**

- Make ordinary generated-adopter text canonical across Windows, macOS, and
  Linux without consulting ambient Git configuration.
- Continue preserving the exact LF and CRLF byte probes as non-text fixtures.
- Prove that ambient and ETHOS-isolated Git observations agree for a repository
  created under a Windows-style global `core.autocrlf=true` policy.

**Non-Goals:**

- Do not inherit ambient Git configuration into ETHOS subprocesses.
- Do not weaken dirty-worktree admission or reinterpret an observation failure
  as clean.
- Do not add platform branches, fallback behavior, or another policy carrier.

## Decisions

1. **The generated adopter owns its text policy in `.gitattributes`.** Add the
   repository-wide rule `* text=auto eol=lf` before the existing
   `line-ending-*.txt -text` exception. This makes ordinary text canonical while
   retaining exact-byte probes. Relying on global `core.autocrlf`, setting a
   local config during fixture creation, or changing the observer were rejected
   because each would make portable repository meaning depend on mutable host
   state.
2. **The regression crosses the actual configuration boundary.** It creates the
   adopter with a temporary global Git configuration containing
   `core.autocrlf=true`, materializes CRLF working-tree bytes for an ordinary
   tracked file, and checks both ambient Git status and `dirty_provenance()`.
   Merely setting repository-local `core.autocrlf` after the initial commit was
   rejected because it does not reproduce the construction-versus-observation
   mismatch.
3. **Production observation remains strict and isolated.** `run_git` and
   `dirty_provenance()` keep hiding ambient global and system configuration.
   The fixture must satisfy the product boundary rather than receive a
   host-specific exception.

## Risks / Trade-offs

- **A blanket text rule could transform intentional binary fixtures** → retain
  the existing explicit `-text` rule and assert byte-for-byte index/worktree
  round trips.
- **A regression could accidentally test only one Git view** → assert ambient
  porcelain status and the production `dirty_provenance()` result separately.
- **The test could mutate the developer's real global Git configuration** → use
  a temporary `GIT_CONFIG_GLOBAL` file scoped to the test process.

## Migration Plan

Update the generated adopter's existing `.gitattributes` owner, add the focused
cross-boundary regression, and run package-acceptance plus Git-observation
checks before full proof. Rollback is the exact parent commit; no repository,
runtime, or host compatibility state is introduced.
