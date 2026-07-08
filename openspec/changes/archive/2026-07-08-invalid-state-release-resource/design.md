# Design

The smallest durable fix is a two-tier read path:

```text
source checkout: system/invalid_states.toml
installed wheel: ethos_core/data/invalid_states.toml
```

`system/invalid_states.toml` remains the source contract. The packaged file is
only a release mirror so installed `ethos-core` can classify gaps without a
repository checkout. A regression test compares parsed TOML payloads, and a
wheel smoke check confirms the resource is included in the artifact.

This preserves the ETHOS boundary: contracts stay contracts, package resources
stay release artifacts, and runtime projection does not mint new truth.
