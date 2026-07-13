# Design

Receipt files are supplied from the absolute directory named by
`ETHOS_SEMANTIC_ATTESTATION_RECEIPT_DIR`; that directory and the resolved
receipt path must be outside the governed repository. A receipt has a strict
schema, self-digest, allow-only verdict, independent reviewer role, nonempty
basis, validity interval, and `mints_authority = false`.

The claim-side declaration binds the receipt id, file digest, scope digest, and
HEAD. Evaluation recomputes the current semantic scope from promotion targets,
then fails closed on any missing, malformed, stale, local, or mismatched fact.
The runtime projects structured attestation state only; it does not grant
authority. Claims that remain `digest_only` never read the receipt directory.

The former top-level `[scope]` was a broad, unused mirror that frequently
disagreed with promotion targets. Removing it leaves one executable scope and
reduces drift without deleting durable evidence, carriers, or promotion paths.
