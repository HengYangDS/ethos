# Design

## Boundary

CI tool supply is an adapter/toolchain concern, not a product semantic center.
The owner surfaces remain small and separated:

- `.config/ci/scripts/download-file.sh` owns transport policy only.
- Tool installers own URL construction, archive validation, extraction, and
  installed command smoke checks.
- `.gitlab-ci.yml` only projects the shared cache into the hosted runner.
- `system/tools.toml` records why the concern exists and which owner surfaces
  participate.

## Mechanism

The helper downloads to `<destination>.part`, resumes partial files with
`--continue-at -`, uses bounded attempts and low-speed detection, and atomically
renames the complete file to the destination. Installers validate archive
readability before reuse and delete invalid archives before a fresh download.

This absorbs the observed failure mode without introducing mirrors, vendored
binaries, a second CI truth store, or a provider-specific ontology.
