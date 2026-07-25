"""SQLite-backed context retrieval index for agentic source-verified retrieval.

Sub-package layout (acyclic DAG: common → schema/sources → indexing/query):

- common    — shared utilities (paths, hashing, git head, manifest lookups)
- schema    — DDL constants and schema initialization
- sources   — source discovery, filtering, and manifest digest
- indexing  — context index rebuild and purge lifecycle
- query     — FTS/symbol search, candidate verification, eval report
"""
