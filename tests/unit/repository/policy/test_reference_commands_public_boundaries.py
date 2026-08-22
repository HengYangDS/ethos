from __future__ import annotations

import pytest

from ethos.repository.policy.references.commands import CommandVocabulary
from ethos.repository.policy.references.commands import command_executables
from ethos.repository.policy.references.commands import command_identity
from ethos.repository.policy.references.commands import normalize_command
from ethos.repository.policy.references.commands import shebang_executable
from ethos.repository.policy.references.commands import shell_commands
from ethos.repository.policy.references.commands import shell_executables


def test_reference_commands_canonical_wrappers_and_scripts() -> None:
    npm_scripts = {
        "quality": {"uv run --python 3.14 pytest", "npm run nested"},
        "nested": {"npx --package prettier@3 prettier --check ."},
    }
    text = """
helper() { echo ignored; }
VALUES=(
  one
  two
)
cat <<'EOF'
python hidden.py
EOF
helper
FOO=1 env -u HOME -- uv run --python 3.14 python -m pytest
npm run quality
"""

    assert shell_executables(text, npm_scripts) == {
        "cat",
        "uv",
        "python",
        "pytest",
        "npm",
        "npx",
        "prettier",
    }
    assert shell_commands(
        "uv run --python 3.14 pytest -q\n",
        {"pytest", "pytest -q"},
        require_declared=True,
    ) == {"pytest -q"}
    assert command_identity(("uv", "run", "pytest", "-q"), {"pytest"}) == "pytest"


def test_reference_commands_malformed_public_inputs_fail_closed() -> None:
    assert normalize_command("  'unterminated  ") == "'unterminated"
    assert shell_executables("echo 'unterminated", {}) == set()
    assert shebang_executable("#!/usr/bin/env 'unterminated") == ""
    assert shebang_executable("#!") == ""
    assert command_executables(("/dev/null",), {}) == set()
    assert command_identity(("/foreign/tool",), {"tool"}, require_declared=True) == ""
    assert command_identity(("tool", "unknown"), {"tool run"}, require_declared=True) == (
        "tool unknown"
    )


def test_reference_commands_do_not_let_a_group_owner_hide_an_unknown_subcommand() -> None:
    """A declared command group cannot authorize an undeclared child command."""
    known = {"ethos", "ethos status", "ethos lane", "ethos lane start"}

    assert command_identity(("ethos", "audit", "--json"), known, require_declared=True) == (
        "ethos audit"
    )
    assert (
        command_identity(("ethos", "lane", "invented", "--json"), known, require_declared=True)
        == "ethos lane invented"
    )
    assert command_identity(("ethos", "--version"), known, require_declared=True) == "ethos"


def test_command_vocabulary_is_reused_across_identity_checks() -> None:
    vocabulary = CommandVocabulary.compile(
        {"ethos", "ethos status", "ethos lane", "ethos lane start"}
    )

    assert command_identity(("ethos", "status", "--json"), vocabulary) == "ethos status"
    assert command_identity(("ethos", "lane", "start", "x"), vocabulary) == "ethos lane start"


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [
        (("env", "--chdir", "/tmp", "python", "-m", "pytest"), {"python", "pytest"}),
        (("env", "--chdir=/tmp", "python", "-m", "pytest"), {"python", "pytest"}),
        (("env", "-u", "HOME", "--", "uvx", "ruff@0.9", "check"), {"uvx", "ruff"}),
        (("npx", "@scope/tool@2", "run"), {"npx", "tool"}),
        (("uvx", "package@1/bin/tool", "check"), {"uvx", "package"}),
    ],
)
def test_reference_commands_canonical_environment_and_package_boundaries(
    tokens: tuple[str, ...], expected: set[str]
) -> None:
    assert command_executables(tokens, {}) == expected
