## Context

`ethos-core` deliberately has no tracked `src/ethos_core/data/` declaration
copies. Hatch projects canonical `system/` declarations into that path while
creating the source distribution. A subsequent wheel build executes from the
unpacked sdist, where the original checkout-relative `../../system/...` paths
do not exist.

## Decision

The sdist remains the only step that reads `../../system/...`. The wheel reads
the corresponding `src/ethos_core/data/...` files that the sdist contains and
maps them to its package-data destination. The architecture test validates the
one-to-one paired mapping, including declarations whose installed names use
underscores. An editable-wheel build has no sdist-local files, so its narrow
Hatch hook supplies the same projection from the checkout canonical sources;
it derives that mapping from the canonical sdist declaration and does not
create tracked copies or make Hatch a runtime dependency.

The new OpenSpec carrier adds four effective YAML lines. The admitted
candidate-train reconciliation allowance moves four category lines from
product Python to YAML. The record allowance and `maximum_total` do not change,
so the accounting remains a hard-cap reallocation rather than a budget reset.

## Consequences

`uv build --all-packages` can now create both the sdist and wheel without
adding a second tracked declaration source. A missing sdist projection or an
incorrect wheel source path fails the focused architecture test and the build
proof gate.
