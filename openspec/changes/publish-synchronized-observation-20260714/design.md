# Design

`publish` remains a local-readiness command. Its existing tracking reducer is
read-only and compares HEAD with a local `origin/<branch>` ref. When that
comparison is `synchronized`, the public publication field should state the
observation rather than retain the generic `deferred` label.

The transition verdict remains `defer` in every no-push case. Thus an observed
remote match cannot be mistaken for an executed publication, and an available
remote that is merely reachable remains `deferred` until a future adapter
actually owns remote mutation.
