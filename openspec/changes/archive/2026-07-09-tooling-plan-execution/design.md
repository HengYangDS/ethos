# Design

This change converts only mechanisms with complete owner surfaces into active
local gates. Each active gate has a catalog entry, configuration owner, reusable
script, CI/template projection, and tests.

`run-dependency-hygiene.sh` runs `deptry` per Python distribution. This avoids
misreading the workspace root as one runtime package and keeps dependency
metadata hygiene separate from vulnerability scanning.

`run-prose-check.sh` runs `codespell` in report-first mode over current
human-facing docs and governance surfaces. It never rewrites files and excludes
archives, generated projections, evidence, and lockfiles.

`run-json-schema-check.sh` validates JSON Schema documents as metaschemas. It is
schema-document hygiene, not a substitute for command payload validation.

`run-hosted-provider-observation.sh` writes a provider-neutral observation
envelope for GitHub and GitLab. Default mode is dry-run/tool-discovery only;
execute mode can query provider CLIs when available. Both modes are observation
evidence and explicitly do not claim repository proof, hosted CI success, or
remote publication.

Vulnerability scanning remains planned. A non-trust-bearing boundary wrapper
records why `pip-audit` cannot yet claim `uv.lock` coverage and what is required
for activation.
