# Design

`product_boundary_report` enumerates product surfaces and applies literal leak
patterns to text files. `.ethos/` is a valid product surface for repository
bindings, but `.ethos/state/` is explicitly ignored local runtime state.

The smallest durable fix is a prefix-level skip for `.ethos/state/**` before the
existing skipped-directory checks. This keeps active `.ethos/*.toml` files in
scope and removes only the host-local runtime subtree.

The regression writes a proof JSON containing a host-local path under
`.ethos/state/proof/` and verifies that only `README.md` is scanned and no
product-boundary gap is reported.
