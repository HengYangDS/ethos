---
subject: ethos:foundations-effects
role: research
state: active
relations:
  part_of: ../modern-engineering-foundations.md
  informs: ../../plans/terminal-governance-product-design.md
  constrained_by: ../../governance/product-design-contract.md
---

# State, Effects And Recovery

Status: active research; dated observations retain their original evidence limits.

Purpose: Compare transition models, native hooks and effect-lifetime guarantees.

See also: [Research Overview](../modern-engineering-foundations.md),
[Product Design Contract](../../governance/product-design-contract.md), and
[Terminal Plan](../../plans/terminal-governance-product-design.md).

## State, Hooks And Effects

### Executed Native Observation Comparison

September 18 source `7711c673648426ce8aace0e267340e02cb593591` changes the next
replacement priority. One closeout case spends approximately 4.36 seconds on
OpenSpec starts and 3.43 seconds on eight native ref updates including hooks;
forty-three profile-object reads consume approximately 0.21 seconds. Counts
alone therefore select the wrong bottleneck.

An isolated Dulwich 1.2.15 trial passes exact-content SHA-1/SHA-256 loose/packed,
linked-worktree, changing-ref and missing/corrupt-object cases. Native `cat-file`
batching also removes most repeated startup cost without a new dependency.
Reopening a packed object reader for every query can regress. Retain native
effects, hooks, signatures and CAS; no production object-library choice follows
from this microbenchmark. Full reftable behavior and Windows remain unqualified.

The locked OpenSpec 1.13.0 package exports its Commander program. An awaited
sequential batch reuses that official parser and command implementation, rather
than constructing a parallel API. Eight reads measured approximately 0.94 seconds
individually and 0.136 seconds batched. Output differs only in native validation
duration fields; native failure exits preserve output and do not execute the
tail. The bounded adapter must verify ordered frames, failure/currentness,
read-only scope, installed-package inclusion and process cleanup before adoption.

The fixed upstream references are OpenSpec commit
`9d4e5974e5c0d9a09b9c6c1e1eb0975e80ec4461`, its exported
`src/cli/index.ts`, Commander 14.0.3 repeated `parseAsync` state restoration, and
Dulwich tag `dulwich-1.2.15`. Raw commands, source metadata and comparisons are
in the existing ignored `build/evidence/quality/commit-integrity/` root under
`throughput-foundation-` and `throughput-official-program-batch-feasibility`.
These experiments qualify a narrow mechanism, not full-product superiority.

[Git's native configured hooks][git-hook] and [configuration contract][git-hook-config]
provide composition without another script dispatcher. The local isolated probe
used command-scoped configuration only; no ETHOS hooks were disabled or modified.
It observed preparing, prepared and committed phases on success, and prepared
rejection followed by aborted. Supported phase handling, hook order, trust and
config precedence require explicit tests before adopting this transport.

This does not solve the current handoff by itself. Adding a successful hook
cannot neutralize an incumbent hook's rejection, and using a generic disable
switch would discard the very boundary being preserved. The remaining design
must let an explicitly authorized exact evaluator run the same substantive
admission once, with normal raw-Git behavior unchanged. If a native mechanism
cannot preserve that obligation, its convenience is not an adoption argument.

[Native ref transactions][git-ref] supply precise old-OID checks and ref effects.
They do not make filesystem, database and multi-Forge effects one global atomic
transaction. Native command observation is not universal interception; there is
no assumed pre-status hook. Pre-tool events, where a host supports them, should
call the existing owner for early failure and context selection. They are not
an agent-independent security boundary for writes made outside that host.

| Layer | Suitable foundation | Required distinction |
| --- | --- | --- |
| Pure legal transitions | Small typed transition model; [pytransitions][pytransitions] or [SCXML][scxml] where hierarchy/events reduce code | A legal transition does not establish fresh facts, permission or effect completion. Do not persist another copy of repository state. |
| UI interaction | XState | [Restoration][xstate] does not rerun completed actions but restarts invocations. It therefore does not guarantee exactly-once external effects. |
| Local process lifetime | Standard-library task groups/timeouts; [AnyIO][anyio-mechanism] if it replaces repeated supervision | Cancellation of a coroutine is not proof that its external process tree stopped. Threads may require cooperation; cover real process death and cleanup. |
| Long-lived external operations | [Temporal][temporal] as an optional execution backend | Durable orchestration can own its attempts/history, not repository intent, Lease or authorization. Require idempotent/observed effects and fresh admission on each effect. |

Prefer a small explicit model and native effects for local repository governance.
A durable engine becomes justified by measured long-lived external coordination,
not as a cure for an ambiguous model. Attempt, effect, durable result and ACK must
remain distinguishable whether implemented directly or through a framework.

### Native Windows Security Metadata

On September 22, exact source `d5008a29e` failed Windows 3.12 and 3.14
package conformance at
`git_object_trust_anchor_observation_unavailable:timeout`. Completed GitHub
jobs `106740192755` and `106740192850` locate the failure in shell-backed ACL
observation during installed full-ref publication. This proves an unavailable
observation, not an unsafe ACL or the precise reason PowerShell stopped responding.

The selected replacement direction is the existing native security boundary,
using [pywin32 b312's Win32 wrappers][pywin32-security] rather than another shell
retry or hand-written ctypes structures. The locked Windows package closure
already includes pywin32. Its documented [read][windows-security-read] and
[write][windows-security-write] APIs return or consume native security descriptors.
Make the platform dependency explicit through native requirement parsing; the
current custom lower-bound regular expression cannot represent environment
markers. Do not add a parallel dependency grammar or permission-policy owner.

Preserve effective caller identity, owner and mutating-ACE checks, protected DACLs,
unchanged content, native failures and cancellation. Missing, malformed or
unsupported observations cannot become successful protection. Thread impersonation,
generic write rights and null DACLs need distinguishing cases; reading metadata
does not grant authority to change it. PowerShell remains with any independently
necessary process-observation owner, not as an ACL fallback.

This direction is not an implemented or qualified Windows repair. Complete native
safe/unsafe/error cases and the installed publication path in the existing
proof-throughput conformance work. Local macOS proof and source inspection do not
establish Windows behavior.

## Sources

Links identify inspected documents, not blanket endorsements. Source-level and
README observations above have different strength; repository popularity and
marketing claims were not used as evidence of comparative performance.

[git-hook]: https://github.com/git/git/blob/e9019fcafe0040228b8631c30f97ae1adb61bcdc/Documentation/git-hook.adoc
[git-hook-config]: https://github.com/git/git/blob/e9019fcafe0040228b8631c30f97ae1adb61bcdc/Documentation/config/hook.adoc
[git-ref]: https://github.com/git/git/blob/e9019fcafe0040228b8631c30f97ae1adb61bcdc/Documentation/git-update-ref.adoc
[pytransitions]: https://github.com/pytransitions/transitions/blob/bd42b38f3627e6bca7274fb4d9af2e105f75da7c/README.md
[scxml]: https://github.com/w3c/scxml/blob/360ce6f05d741987940ed7db01bc46b319102ad9/README.md
[xstate]: https://github.com/statelyai/docs/blob/54827bcf6591935ae1dc13484eafca88d3b4cf7a/content/docs/persistence.mdx
[anyio-mechanism]: https://github.com/agronholm/anyio/blob/4e72d8667818d4a972a549cd910a4e4340c504a0/docs/cancellation.rst
[temporal]: https://github.com/temporalio/sdk-python/blob/ab25ed693f7ec77589346e66c98db299a8c9c9fe/README.md

[pywin32-security]: https://github.com/mhammond/pywin32/blob/2a277cb5552756c2b4d42b524dc36d25e0bb6354/win32/src/win32security.i
[windows-security-read]: https://mhammond.github.io/pywin32/win32security__GetNamedSecurityInfo_meth.html
[windows-security-write]: https://mhammond.github.io/pywin32/win32security__SetNamedSecurityInfo_meth.html
