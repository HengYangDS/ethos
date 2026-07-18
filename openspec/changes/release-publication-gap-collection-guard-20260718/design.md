## Decision

`publication_topology` remains the producer of topology diagnostics. The
release-policy reducer accepts only its declared list shape. A malformed
read-model value is ignored rather than string-expanded, so it cannot create
fictional gap IDs. Valid list entries remain losslessly propagated.

This is a compatibility guard at a typed boundary, not a publication
relaxation: the authoritative topology reader still decides whether a real
configuration is invalid.
