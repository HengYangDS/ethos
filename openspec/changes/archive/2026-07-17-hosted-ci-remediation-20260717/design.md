## Context

Pipeline 2866 failed when a broad fixture stub made Docker appear available; pipeline 2867 disconnected before `pip-audit` returned JSON. The current owner script had no retry boundary.

## Goals / Non-Goals

**Goals:** hermetic fixture coverage, one bounded classified retry, and fail-closed scanner evidence.

**Non-Goals:** workflow, dependency, credential, topology, foreign-lane, or historical-pipeline changes.

## Decisions

1. Stub the Docker-context helper only in the materialization test; production discovery is unchanged.
2. Retry once only for explicit transport-disconnect diagnostics. All other failures remain final.
3. Exercise the existing shell owner script with a fake `uv` in the existing architecture test module.

## Risks / Trade-offs

- Broad classification could mask failures → match only explicit transport phrases.
- Retry delays failure → fixed two-attempt bound and one-second default delay.
- The compact proof carrier grows tracked source → one exact, temporary source-budget debt record covers only its measured categories.

## Migration Plan

The change is backward compatible. Reverting the commit restores the former fixture and one-attempt audit behavior; no state or external configuration migrates.
