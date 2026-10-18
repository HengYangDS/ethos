"""A finite shared software vocabulary preserves native prose rejection.

Names come from pyproject.toml, uv.lock and .config/mise/config.toml. Technical
terms follow the Python sys API and Git glossary; shared data words follow the
Department vocabulary. Corpus findings are evidence, never acceptance authority.
References: https://docs.python.org/3.12/library/sys.html and
https://git-scm.com/docs/gitglossary.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.materialization.native_supply import resolve_native_tool
from ethos.repository.release.resources import canonical_resource

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "prose",
    [
        "Use uv, pytest, Pytest, Nox, Pydantic, Cyclopts and codespell.",
        "Read argv, cwd, stdin, stdout and stderr from the subprocess.",
        "Keep the preimage and postimage; compare preimages and postimages.",
        "Inspect namespaces, basenames, docstrings, serializers and initializers.",
        "The rebase is unstaged; rebasing preserves the subtree and subtrees.",
        "Check liveness, reachability, idempotency, postconditions and backpressure.",
        "Trace dataclasses, booleans, enums, coroutines and tracebacks in the stdlib.",
        "Keep readback, lockfiles, subpackages and a deduplicated monorepo.",
        "The changelog is ready. Changelogs record changes.",
        "Use a prettier flat cache directory. Prettier formats the file.",
        "Git's preimage is preserved; the verifier's report is auditable.",
        "Use backfills and backtests; assess missingness during onboarding.",
        "Use actionlint, Gitleaks, Syft, Deptry, mutmut, shfmt and yamllint.",
        "A JUnit report records APIs, ABIs, SDKs, OIDs and TTLs.",
        "Keep allowlists and allowlisted configs; the README and READMEs agree.",
        "Inspect inode and inodes; retain a readback and multiple readbacks.",
        "Validate the preflight and preflights before using a preflighted result.",
        "Namespaces are namespaced; a rebase rebases and a branch is rebased.",
        "The serializer uses an initializer, a docstring, a dataclass and an enum.",
        "A coroutine reports a traceback; subtests exercise each subtest.",
        "A monorepo keeps monorepos, repos and repo names distinct.",
        "Deduplicate dataflow; deduplication keeps a deduplicated result.",
        "Check canonicalization and idempotently apply changes in the middleware.",
        "Preserve discoverability and recoverability; lossy output is not losslessly copied.",
        "A basename belongs to a namespace; preconditions and postconditions differ.",
        "Shards are sharded; sharding retains a subpackage and subpackages.",
        "The dunder and dunders are language names; pytest's report is ready.",
        "Use CSpell and textlint; Textlint checks prose on Debian Trixie.",
        "DRs qualify uncategorized, unencrypted and unscoped inputs.",
        "Keep unignored files before unpausing the runner.",
    ],
)
def test_native_software_vocabulary_accepts_canonical_usage(tmp_path: Path, prose: str) -> None:
    """Exact dependency and technical spellings work in actual Markdown files."""
    source = tmp_path / "software [literal].md"
    source.write_text(f"# Guide\n\n{prose}\n", encoding="utf-8")
    original = source.read_bytes()
    result = run_command(
        tmp_path,
        (
            str(resolve_native_tool("vale")),
            "--no-global",
            f"--config={canonical_resource('.config/checks/vale/vale.ini')}",
            "--output=JSON",
            "--no-color",
            str(source),
        ),
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not result.stderr
    assert not any(json.loads(result.stdout).values())
    assert source.read_bytes() == original


@pytest.mark.parametrize(
    ("prose", "check", "match"),
    [
        ("The veriified report is ready.", "Vale.Spelling", "veriified"),
        ("The qzxwvvv report is ready.", "Vale.Spelling", "qzxwvvv"),
        ("The preimgae is ready.", "Vale.Spelling", "preimgae"),
        ("The namespcae is ready.", "Vale.Spelling", "namespcae"),
        ("Use Cspell for review.", "Vale.Terms", "Cspell"),
        ("Use Github for review.", "Vale.Terms", "Github"),
        ("Use Gitlab for review.", "Vale.Terms", "Gitlab"),
        ("Read the the report.", "Vale.Repetition", "the the"),
        ("We utilize the data.", "plain.concise", "utilize"),
        (
            "This offers a rich tapestry of insights.",
            "plain.stock-phrases",
            "rich tapestry of insights",
        ),
    ],
)
def test_native_software_vocabulary_keeps_adverse_findings(
    tmp_path: Path,
    prose: str,
    check: str,
    match: str,
) -> None:
    """A glossary cannot grant typos or weak prose a passing native result."""
    source = tmp_path / "defect.md"
    source.write_text(f"# Guide\n\n{prose}\n", encoding="utf-8")
    original = source.read_bytes()
    result = run_command(
        tmp_path,
        (
            str(resolve_native_tool("vale")),
            "--no-global",
            f"--config={canonical_resource('.config/checks/vale/vale.ini')}",
            "--output=JSON",
            "--no-color",
            str(source),
        ),
        timeout=20,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert not result.stderr
    assert any(
        item["Check"] == check and item["Match"] == match and item["Line"] == 3
        for item in json.loads(result.stdout).get(str(source), ())
    ), result.stdout
    assert source.read_bytes() == original


def test_native_software_vocabulary_separates_prose_and_literal_code(tmp_path: Path) -> None:
    """An unseen typo is inert in code but rejected at its original prose coordinates."""
    source = tmp_path / "literal [scope].md"
    contents = (
        "# Guide\n\nKeep `veriified qzxwvvv Github Gitlab utilize the the` literal.\n\n"
        "```text\nveriified qzxwvvv Github Gitlab utilize the the\n```\n\n"
        "The report is ready.\n"
    )
    source.write_text(contents, encoding="utf-8")
    original = source.read_bytes()
    command = (
        str(resolve_native_tool("vale")),
        "--no-global",
        f"--config={canonical_resource('.config/checks/vale/vale.ini')}",
        "--output=JSON",
        "--no-color",
        str(source),
    )
    result = run_command(tmp_path, command, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not result.stderr
    assert not any(json.loads(result.stdout).values())
    assert source.read_bytes() == original

    source.write_text(
        contents.replace("The report is ready.", "The veriified report is ready."),
        encoding="utf-8",
    )
    original = source.read_bytes()
    result = run_command(tmp_path, command, timeout=20)
    assert result.returncode == 1, result.stdout + result.stderr
    assert not result.stderr
    findings = json.loads(result.stdout)
    assert set(findings) == {str(source)}
    assert {
        (item["Check"], item["Match"], item["Line"], tuple(item["Span"]))
        for item in findings[str(source)]
    } == {("Vale.Spelling", "veriified", 9, (5, 13))}, result.stdout
    assert source.read_bytes() == original
