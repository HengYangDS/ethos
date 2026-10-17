# Proposal

## Why

Active Change artifacts escape both the shared 512-nonblank-line Markdown ceiling, which exempts them, and the official templates, which official strict validation does not inspect. On 2026-10-17, across the dev heads of the nine governed repositories outside the deferred alphasim and di-effect families, eight active artifacts in three repositories exceed the ceiling or omit official headings, including a design of 2,959 nonblank lines. Ten MODIFIED requirements in four active Changes also exceed the 500 characters that strict validation of archived specifications allows; change validation does not check them, so each Change fails only when it is archived (observation Attestation `4debe0d2`).

## What Changes

- **BREAKING:** An active Change's proposal, design, tasks and delta specs fall under the shared Markdown ceiling. This reverses the OpenSpec carrier exemption in "Current Markdown stays within one navigable topic". The immutable archive keeps its captured bytes, and accepted specifications keep their exemption until their capabilities are split.
- **BREAKING:** Each active proposal and design contains the literal headings of the template that the official CLI resolves for its schema, in template order.
- Proof of a selected active Change first archives it with the official CLI in a disposable projection of the exact head and requires official strict validation of the resulting specifications, so an unarchivable Change fails before its gates run.
- These checks reach every governed repository through its existing plan and proof evaluation.
- Out of scope: splitting accepted specifications, bounding task wording, and checks that official strict validation already performs. Retiring `proof-throughput` precedes this Change and is not part of it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: the Markdown ceiling bounds active OpenSpec Change artifacts. Its delta is written in task 2.2, once `proof-throughput` has archived the requirement it modifies.
- `repository-governance`: active proposals and designs follow their resolved official templates, and proof requires an archivable Change.

## Impact

- Code: the document-length boundary in `src/ethos/repository/registry/docs/health.py`, the template-structure reader and the archive simulation under `src/ethos/adapters/openspec/lifecycle/`, and the OpenSpec governance report that runs them.
- Governed repositories: active Changes in aigw-cli, data-department-work-guidelines and openai-responses-proxy conform before their owners rebind to a runtime with these checks; ETHOS conforms once `proof-throughput` is retired.
- Cost: the governance report's existing read batch gains one artifact-graph read for all active Changes and one template read per distinct schema; proof of a selected Change gains one official archive and one strict validation of a disposable projection.
