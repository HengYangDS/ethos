## Context

See [proposal.md](proposal.md). The full proof already declares
`local-install-smoke` as a package gate after `build`, but
`unit-architecture` collects a second end-to-end test that bootstraps an
installed runtime, activates hooks, starts a Work Lane, and exercises retirement
recovery. The dedicated gate passed in the same proof where the duplicate test
lost an xdist worker. The exact worker-loss cause is not proven because the
worker's final timeout dump was not retained; duplicate execution ownership and
resource amplification are proven directly by the gate graph and test body.

## Goals / Non-Goals

**Goals:**

- Give the complete package-only lifecycle one execution owner and one
  HEAD-bound receipt.
- Preserve every unique package-runtime assertion currently proved only by the
  duplicate architecture test.
- Keep architecture tests fast and deterministic by limiting them to
  declarations, orchestration, portability, and pure contracts.
- Make the physical layout express package delivery rather than retain a
  top-level historical filename.

**Non-Goals:**

- No timeout increase, worker restart, retry, test skip, or serial-only escape.
- No new gate, receipt schema registry, persistent state, compatibility import,
  or package lifecycle.
- No new runtime, lane, Lease, retirement, or adopter state-machine semantics.
  When the ordinary-wheel lifecycle exposes a violation of an existing product
  invariant, repair that invariant at its existing owner rather than weakening
  the acceptance run or introducing package-only behavior.
- No claim that the observed worker loss was definitively caused by pytest's
  timeout without preserved diagnostic evidence.

## Decisions

### The package gate owns real lifecycle execution

The existing delivery pipeline will invoke one package acceptance owner after
the wheel build. That owner will reuse the installed wheel and its signed
adopter fixture to prove hook/runtime activation, package-only successor
materialization, runtime relocation and repair, first-lane bootstrap, resumable
retirement, and immutable version readback. These observations extend the
existing local-install receipt; they do not create another evidence root.

Keeping the lifecycle in `unit-architecture` was rejected because a unit gate
cannot be both the complete source test owner and a second package release
owner. Adding another package gate was rejected because the existing gate is
already the declared owner.

### Semantic ownership precedes physical projection

The terminal ownership graph is derived from the propositions being proved,
not from the current filenames:

| Owner | Unique invariant | Explicit exclusion |
| --- | --- | --- |
| Delivery pipeline | Orders build and exactly one package-acceptance transaction. | It does not prepare a second environment, decide acceptance, or construct adopter state. |
| Runtime supply | Installs the exact lock-bound production closure into the acceptance transaction's sole environment. | It owns no environment lifecycle, product-wheel installation, or evidence. |
| Package-acceptance effect | Owns one transient root and environment, invokes runtime supply once, installs the wheel without resolving dependencies again, executes the bounded lifecycle, and returns post-observed stage results. | It does not define the gate graph or manufacture a passing receipt. |
| Installed-command observation | Executes an exact installed CLI argv, validates its public `EthosResult`, and preserves the exit code and stderr for runtime and lane acceptance. | It owns no command policy, retry, decision, lifecycle state, or persistence. |
| Acceptance receipt | Rejects incomplete stage sets and renders the exact HEAD/wheel/runtime observations. | It performs no filesystem, process, Git, or runtime effect. |
| Adopter fixture | Constructs the smallest signed repository topology needed by package acceptance. | It owns no product verdict or persistent adopter compatibility state. |
| Runtime acceptance | Proves package-only activation, immutable identity, relocation, repair, and production-only dependencies. | It does not own Work Lane semantics. |
| Lane acceptance | Proves first-lane admission and receipt-bound retirement recovery through public commands. | It does not edit Lease state directly or import test support. |

These owners project under the existing `tools/ci/delivery/` boundary because
they jointly describe delivery of one built package. Package acceptance is a
subpackage only because it has several independently changing invariants and
consumers; it is not introduced to satisfy a line count or directory pattern.
The historical top-level owner and duplicate architecture executor are deleted
after their unique semantics have moved. No forwarding module, import alias, or
compatibility path remains.

### Architecture retains only non-executing contracts

Gate ordering and offline policy remain gate-declaration contracts. Project
runtime selection and host Git overlay remain test-runner contracts. Portable
line endings remain an adopter-fixture contract. Canonical semantic vectors
remain kernel contracts. The obsolete package-smoke architecture executor will
be deleted once no unique assertion remains. Tests may verify semantic import
and execution boundaries, but a particular filename is not itself a product
behavior.

### One receipt records the complete accepted result

The local-install receipt will retain its current identity and add structured
observations for runtime activation, relocation/self-repair, lane bootstrap,
retirement recovery, and immutable version identity. A stage that does not
complete fails the gate before a passing receipt is written. The effect first
removes its exact owned transient root, including sealed runtime content, and
only then publishes the passing receipt; failed cleanup therefore cannot leave
a passing receipt. The owner does not retry a failed lifecycle or manufacture
partial success.

### The ordinary wheel exercises existing semantics without host assumptions

The package run is not a second implementation of runtime or lane semantics. It
calls the public command plane and exposes assumptions that source-checkout or
selected-runtime execution can otherwise hide. Repairs remain with their
existing owners: the acceptance transaction creates one environment, runtime
supply installs the locked production closure into it exactly once, and the
ordinary wheel is then installed into that same environment without dependency
resolution. Lane creation observes the current accepted checkout while
retaining the candidate object as its desired base; hook launch and process
observation do not depend on ambient `PATH`; and the existing generated-tree
remover owns cleanup of sealed runtime content. A failed subprocess preserves
the structured command result and captured stderr so the acceptance boundary
does not erase `required_gaps` or the public `next_action`.

## Risks / Trade-offs

- **The dedicated package gate becomes broader** → it already owns package
  acceptance; reuse one built wheel and one bounded fixture topology so total
  full-proof work decreases rather than duplicating setup.
- **Lifecycle cleanup can leave generated state after a hard process kill** →
  keep all smoke state under the existing owned build root; crash scavenging and
  shared runtime supply remain the separate temporary-resource convergence
  batch and are not hidden here.
- **Cross-platform behavior can differ** → retain the existing host
  conformance matrix and portable executable/path helpers while moving only the
  execution owner.
- **Removing the old module path can expose consumers** → update all active
  imports and declarations in one cutover and require repository-wide reference
  closure; archived records remain immutable history.

## Migration Plan

1. Add failing contracts for the complete package receipt, single execution
   owner, and effect-free Python architecture surface.
2. Establish the semantic delivery owners and extend the same smoke run with
   the unique package-runtime lifecycle assertions.
3. Absorb remaining pure assertions into their existing test owners, delete the
   duplicate lifecycle and old module path, and close active references.
4. Run focused architecture and delivery tests, the real build/install smoke,
   and one exact-HEAD full proof before normal archive and exact-CAS closeout.
