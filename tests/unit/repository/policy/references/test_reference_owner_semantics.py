"""Reference identities keep their native kinds: commands, executables, imports and terms."""

from __future__ import annotations

import difflib
from typing import TYPE_CHECKING

import cyclopts
import pytest

from ethos.adapters.admission.patch_admission import patch_admission
from ethos.repository.policy.references.closure import product_reference_gaps
from ethos.repository.policy.references.declarations import command_owner_sources_from_files
from ethos.repository.policy.references.declarations import native_owned_references_from_files
from ethos.repository.policy.references.observation import installed_distribution_modules
from ethos.repository.policy.references.observation import product_references_from_files
from ethos.repository.policy.references.python_syntax import complete_python_tree
from tests.support.governed_repository import git

if TYPE_CHECKING:
    from pathlib import Path

LITERAL_TOOL = (
    "import cyclopts\n"
    "app = cyclopts.App(name='tool')\n"
    "sub = cyclopts.App(name='lane')\n"
    "app.command(sub)\n"
    "@sub.command\n"
    "def start_now(): pass\n"
    "@sub.command(name='stop')\n"
    "def halt(): pass\n"
    "@sub.command\n"
    "def _private_step(): pass\n"
    "@sub.command(name=VALUE)\n"
    "def dynamic(): pass\n"
)


def test_application_variables_declare_no_command() -> None:
    """A Cyclopts variable or a non-literal name is not what a user types."""
    files = {
        "src/tool/cli.py": (
            "import cyclopts\n"
            "app = cyclopts.App(name=PUBLIC_COMMAND)\n"
            "@app.default\n"
            "def run_command(): pass\n"
            "@app.command\n"
            "def check(): pass\n"
        ),
    }
    document = {"docs/guides/runbook.md": "| Account | `app` |\n|---|---|\n"}

    observed = product_references_from_files(
        document, context_files=files, include_declarations=False
    ).references

    assert command_owner_sources_from_files(files) == {}
    assert observed["command"] == set()
    assert observed["executable"] == set()


def test_unowned_decorators_and_unnamed_parents_declare_no_command() -> None:
    """Another framework's decorator or an unnamed root above a named App owns no identity."""
    files = {
        "src/pkg/cli.py": "from cyclopts import App\napp = App()\n",
        "src/pkg/typed.py": (
            "import typer\n"
            "app = typer.Typer()\n"
            "doctor = typer.Typer()\n"
            "@app.command('graph')\n"
            "def graph(): pass\n"
            "@doctor.command('plan')\n"
            "def plan(): pass\n"
        ),
        "src/pkg/raw.py": (
            "from cyclopts import App\n"
            "root = App()\n"
            "sub = App(name='getraw')\n"
            "root.command(sub)\n"
            "@sub.command\n"
            "def fetch(): pass\n"
        ),
    }

    assert command_owner_sources_from_files(files) == {}


def test_literal_names_keep_exact_cyclopts_identities() -> None:
    """Literal names compose fully named paths; a function name follows Cyclopts' transform."""
    owners = command_owner_sources_from_files({"src/tool/cli.py": LITERAL_TOOL})

    assert set(owners) == {
        "tool",
        "tool lane",
        "tool lane start-now",
        "tool lane stop",
        "tool lane private-step",
    }
    assert owners["tool lane stop"] == frozenset({"src/tool/cli.py:halt"})


@pytest.mark.parametrize("function", ["start_now", "_private_step", "HTTPServer", "runV2Now"])
def test_function_command_names_follow_the_documented_cyclopts_rule(function: str) -> None:
    """The rule ETHOS models gives the name Cyclopts itself serves for the same function."""
    source = (
        f"from cyclopts import App\napp = App(name='tool')\n@app.command\ndef {function}(): pass\n"
    )

    owners = command_owner_sources_from_files({"src/tool/cli.py": source})

    assert set(owners) == {"tool", f"tool {cyclopts.default_name_transform(function)}"}


def test_a_bare_prose_word_is_a_term() -> None:
    """A single word names a term; a multi-token span still meets the declared vocabulary."""
    context = {"src/tool/cli.py": LITERAL_TOOL}
    declared = command_owner_sources_from_files(context)
    term = {"docs/guides/accounts.md": "The account `tool` is reserved.\n"}
    invocation = {"docs/guides/accounts.md": "Run `tool lane frobnicate` first.\n"}

    bare, used = (
        product_references_from_files(
            document, context_files=context, declared_commands=declared, include_declarations=False
        )
        for document in (term, invocation)
    )

    assert bare.references["command"] == set()
    assert bare.references["executable"] == set()
    assert used.references["command"] == {"tool lane frobnicate"}


def test_package_relative_imports_stay_inside_their_package() -> None:
    """A relative import is neither a top-level import nor a standard-library sink."""
    source = (
        "from ._access.policy import load\n"
        "from .subprocess import run\n"
        "from . import sibling\n"
        "run(['frobnicate'])\n"
    )

    observed = product_references_from_files(
        {"src/pkg/module.py": source}, include_declarations=False
    ).references

    assert observed["import"] == set()
    assert observed["executable"] == set()


def test_repository_tree_owns_its_first_party_modules() -> None:
    """Root and leading `src/` modules are first-party; nothing else is excused by name."""
    files = {
        "noxfile.py": "",
        "src/web_ingestion/__init__.py": "",
        "src/narration_target.py": "",
        "tests/test_cli.py": "",
        "examples/demo/src/model.py": "",
    }

    owned = native_owned_references_from_files(files)
    gaps = product_reference_gaps(owned, {"import": {"tools", "ethos", "model", "web_ingestion"}})

    assert {"noxfile", "src", "web_ingestion", "narration_target", "tests"} <= owned["import"]
    assert gaps == [
        "product_reference_not_admitted_at_baseline:import:ethos",
        "product_reference_not_admitted_at_baseline:import:model",
        "product_reference_not_admitted_at_baseline:import:tools",
    ]


def test_pixi_environment_maps_declared_distributions(tmp_path: Path) -> None:
    """A pixi environment's metadata maps a declared distribution as `.venv` does."""
    site = tmp_path / ".pixi/envs/default/lib/python3.12/site-packages"
    for name, modules in (("PyYAML", "_yaml\nyaml\n"), ("Extra", "extra_module\n")):
        (site / f"{name}-1.0.dist-info").mkdir(parents=True)
        (site / f"{name}-1.0.dist-info/METADATA").write_text(f"Name: {name}\n", encoding="utf-8")
        (site / f"{name}-1.0.dist-info/top_level.txt").write_text(modules, encoding="utf-8")
    project = '[project]\nname = "adopter"\ndependencies = ["PyYAML"]\n'

    owned = native_owned_references_from_files(
        {"pyproject.toml": project}, distribution_modules=installed_distribution_modules(tmp_path)
    )

    assert {"_yaml", "yaml"} <= owned["import"]
    assert "extra_module" not in owned["import"]


def test_patch_admission_reports_every_refused_reference(tmp_path: Path) -> None:
    """One admission names each undeclared reference; the first remains its reason."""
    repo = tmp_path / "adopter"
    (repo / "tools").mkdir(parents=True)
    git(repo, "init", "-b", "dev")
    path = "tools/run.sh"
    before = "echo start\n"
    (repo / path).write_text(before, encoding="utf-8")
    git(repo, "add", ".")
    baseline = git(repo, "write-tree")
    patch = f"diff --git a/{path} b/{path}\n" + "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            (before + "frobnicate --now\nquux --all\n").splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )

    report = patch_admission(
        root=repo, requested_paths=(path,), baseline_head=baseline, patch=patch
    )

    assert report["reason"] == "product_reference_not_admitted_at_baseline:executable:frobnicate"
    assert report["required_gaps"] == [
        "product_reference_not_admitted_at_baseline:executable:frobnicate",
        "product_reference_not_admitted_at_baseline:executable:quux",
    ]


def test_a_syntax_warning_does_not_make_valid_python_unparseable() -> None:
    """An invalid escape warns at compile time but remains complete Python syntax."""
    assert complete_python_tree('import re\nPATTERN = re.compile("\\d+")\n') is not None
