"""Resolve native command vocabulary without laundering unknown subcommands."""

from __future__ import annotations

import shlex

import pytest

from ethos.repository.policy.references.commands import CommandVocabulary
from ethos.repository.policy.references.commands import command_executables
from ethos.repository.policy.references.commands import command_identity
from ethos.repository.policy.references.commands import command_invocation
from ethos.repository.policy.references.commands import normalize_command
from ethos.repository.policy.references.commands import shebang_executable
from ethos.repository.policy.references.commands import shell_commands
from ethos.repository.policy.references.commands import shell_configuration_inputs
from ethos.repository.policy.references.commands import shell_executables
from ethos.repository.policy.references.observation import product_references_from_files


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("env X=1 git status --short", True),
        ("sudo -u root git status", True),
        ("printf value >(git status)", True),
        ("cat <<(git status)", True),
        ("true && git status", True),
        ("node tools/check.mjs", True),
        ("./tools/check.mjs --verify", True),
        ("source ./setup", True),
        ("echo value", None),
        ("uv run ./tools/check.mjs", True),
        ("cat <(uv run ./tools/check.mjs)", True),
        ('python "a>b.py" --verify', True),
        ("rm notes", None),
        ("curl example.com", None),
        ("./tools/check.mjs", False),
        ("node", False),
        ("node represents an executable host.", False),
        ("rm describes a file-removal command.", False),
        ("Each repository's profile owns current behavior.", False),
        ("See docs/proof.md for the evidence.", None),
        ("a < b is a comparison, not an execution request.", False),
        ("'unterminated", None),
    ],
)
def test_native_invocation_shape_preserves_reference_and_uncertainty(
    source: str, *, expected: bool | None
) -> None:
    """Syntax and positive identities classify inputs without a command blacklist."""
    vocabulary = CommandVocabulary.compile({"git status"})

    assert command_invocation(source, vocabulary) is expected


def test_native_invocation_inspection_never_evaluates_payload(tmp_path, monkeypatch) -> None:
    """Ambient variables and command substitution never authorize evaluation."""
    marker = tmp_path / "unexpected-effect"
    vocabulary = CommandVocabulary.compile({"git status"})
    monkeypatch.setenv("FLAGS", "not a command")

    assert command_invocation(f"git status $(touch '{marker}')", vocabulary) is True
    assert command_invocation("git status $FLAGS", vocabulary) is True
    assert not marker.exists()


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
scanner \\
  --scan .
"""

    assert shell_executables(text, npm_scripts) == {
        "cat",
        "uv",
        "python",
        "pytest",
        "npm",
        "npx",
        "prettier",
        "scanner",
    }
    assert shell_commands(
        "uv run --python 3.14 pytest -q\n",
        {"pytest", "pytest -q"},
        require_declared=True,
    ) == {"pytest -q"}
    assert command_identity(("uv", "run", "pytest", "-q"), {"pytest"}) == "pytest"


@pytest.mark.parametrize("quote", ["'", '"'])
def test_reference_commands_preserve_multiline_quoted_arguments(quote: str) -> None:
    """Quoted program text stays data while adjacent commands remain observable."""
    program = "\nNF != 2 { next }\nEND { print selected }\n"
    command = f"awk {quote}{program}{quote}; scanner --scan .\ncollector input\n"
    flattened = (
        f"awk {quote}{program.replace(chr(10), ' ')}{quote}; scanner --scan .\ncollector input\n"
    )
    expected = {"awk", "scanner", "collector"}

    assert shell_executables(command, {}) == shell_executables(flattened, {}) == expected
    assert shell_commands(command, expected) == expected
    assert (
        product_references_from_files({"tools/example.sh": command}).references["executable"]
        == expected
    )


def test_reference_commands_do_not_resume_inside_unterminated_quoted_data() -> None:
    """A malformed quoted argument cannot invent executables from its body."""
    assert shell_executables("awk '\nNF { next }\nEND { print selected }", {}) == set()


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
    vocabulary = CommandVocabulary.compile({"tool", "tool 'unterminated"})
    assert [command for _tokens, command in vocabulary.identities] == ["tool"]


@pytest.mark.parametrize("executable", ["123", "then", "--native-probe"])
def test_reference_commands_keep_native_argv_zero_as_the_executable(executable: str) -> None:
    """Native argv has no shell prefixes; later data cannot become the program."""
    tokens = (executable, "argument")

    assert command_executables(tokens, {}) == {executable}
    assert command_identity(tokens, {executable}) == executable


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
    ("tokens", "expected", "modules"),
    [
        (("env", "--chdir", "/tmp", "python", "-m", "pytest"), {"python"}, {"pytest"}),
        (("env", "--chdir=/tmp", "python", "-m", "pytest"), {"python"}, {"pytest"}),
        (("env", "-u", "HOME", "--", "uvx", "ruff@0.9", "check"), {"uvx", "ruff"}, set()),
        (("npx", "@scope/tool@2", "run"), {"npx", "tool"}, set()),
        (("uvx", "package@1/bin/tool", "check"), {"uvx", "package"}, set()),
        (("python", "-B", "-I", "-m", "ethos.cli"), {"python"}, {"ethos"}),
        (("python", "-m", "foreign.module"), {"python"}, {"foreign"}),
        (("python", "-cpass", "-m", "not_imported"), {"python"}, set()),
        (("python", "script.py", "-m", "not_imported"), {"python"}, set()),
        (("python", "-X", "dev", "-m", "pytest"), {"python"}, {"pytest"}),
        (("python", "-mpytest"), {"python"}, {"pytest"}),
        (("python", "--version", "-m", "not_imported"), {"python"}, set()),
        (("python", "-m"), {"python"}, set()),
        (("python", "-B"), {"python"}, set()),
        (("env", "-i", "python", "-m", "pytest"), {"python"}, {"pytest"}),
        (("env", "-i"), set(), set()),
        (("npx", ">log", "prettier"), {"npx"}, set()),
        (("npx", "--", "prettier", "--check"), {"npx", "prettier"}, set()),
        (("npx", "--yes"), {"npx"}, set()),
    ],
)
def test_reference_commands_canonical_environment_and_package_boundaries(
    tokens: tuple[str, ...], expected: set[str], modules: set[str]
) -> None:
    observed = product_references_from_files({"tools/run.sh": shlex.join(tokens)}).references
    assert observed["executable"] == expected
    assert observed["import"] == modules


@pytest.mark.parametrize(
    ("text", "inputs", "unknown"),
    [
        (
            "prettier --check --config .prettierrc --ignore-path .prettierignore .",
            {".prettierrc", ".prettierignore"},
            False,
        ),
        ("npx prettier --config=cfg.json --no-config --ignore-path=ignore .", {"ignore"}, False),
        ("env -i -- prettier --config cfg.json .", {"cfg.json"}, False),
        ("uv run prettier --config cfg.json .", {"cfg.json"}, False),
        ("prettier --check -- --config cfg.json", set(), False),
        ("prettier --config", set(), True),
        ("prettier --config --check .", set(), True),
        ("cd site && prettier --config cfg.json .", set(), True),
        ("env --chdir=site prettier --config cfg.json .", set(), True),
        ("prettier --config $CONFIG .", set(), True),
        ("prettier --check 'unterminated", set(), True),
    ],
)
def test_prettier_configuration_inputs_are_explicit_or_unknown(
    text: str, inputs: set[str], *, unknown: bool
) -> None:
    """Only explicit static options are inputs; dynamic or malformed shell stays unknown."""
    assert shell_configuration_inputs(text) == (inputs, unknown)
