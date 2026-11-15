# Proposal

## Why

Five results say less than the reader needs, or more than they prove. Each was measured by the
release lane or by a governed repository's session under 0.2.0-beta.10:

- The link gate prints an exit status and reports `gate_failed`. The redirecting URLs sit in the
  proof's payload as a string inside another report's output.
- The staged size check reports one file for each refusal: eight files over the ceiling cost
  eight rounds.
- The audit's repair text for a version source proposes the manifest's PEP 440 version for
  `VERSION`, which the release then refuses as no semantic version.
- A document's front matter counts toward the document ceiling, 5 to 7 lines for each document.
- The hosted journey's foreign-attestation case no longer isolates the attestation check. Mise
  refuses the lock entry that names another release's asset by its URL, before any attestation is
  read. The journey proves that foreign bytes are refused, and its docstring claims more.

## What Changes

- The link gate's gap carries each redirecting URL and its target.
- The staged size check reports every file over the ceiling in one refusal.
- The version-source repair proposes a value that the release accepts.
- The document ceiling measures the body.
- The journey's docstring and the design sentence state what the case proves.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

Four checks' results and one docstring. Each narrows or clarifies a refusal, which the law freeze
admits; none adds a rule.

Owner: the release lead. Next action: write and measure each patch as its own small Change, or as
one when they share a file. Read again: at the cut of 0.2.0-beta.12.
