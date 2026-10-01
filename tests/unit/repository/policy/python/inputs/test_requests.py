"""Separate native consumers of formal inputs from unknown concrete behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.closure import repository_semantic_closure
from ethos.repository.policy.references.observation import reference_consumer_sources_from_files
from tests.support.architecture import declare_reference_package
from tests.support.architecture import declare_reference_surface
from tests.support.architecture import write_reference_source

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("definition", "kind", "parameter"),
    [
        ("def launch(argv):\n subprocess.run(argv)", "executable", "argv"),
        ("def read(name):\n os.getenv(name)", "value", "name"),
        ("def launch(argv, **options):\n subprocess.run(argv, **options)", "executable", "argv"),
        ("def launch(argv):\n subprocess.run(argv, check=False)", "executable", "argv"),
    ],
)
def test_formal_native_input_retains_a_conditional_request(
    definition: str, kind: str, parameter: str
) -> None:
    """A function input is a known relation, not a guessed concrete executable or key."""
    observed = reference_consumer_sources_from_files(
        {"src/example/probe.py": "import os, subprocess\n" + definition}
    )

    assert observed.unknown_consumers == {}
    requests = observed.requests
    assert len(requests) == 1
    assert requests[0].kind == kind
    assert parameter in {item.name for item in requests[0].inputs}
    assert requests[0].path == "src/example/probe.py"
    assert observed.sources[kind] == {}


@pytest.mark.parametrize(
    "source",
    [
        "def launch(argv):\n subprocess.run(argv)\nlaunch(compute())",
        "def launch(argv):\n subprocess.run(transform(argv))",
        "def launch(argv):\n subprocess.run(['git'], executable=transform(argv))",
        "def launch(argv):\n getattr(subprocess, argv)(['git'])",
        "subprocess.run(argv)",
        "def launch(argv):\n mutate(argv)\n subprocess.run(argv)",
        "def launch(argv):\n subprocess.run(argv, args=['git'])",
        "def launch(argv):\n subprocess.run(argv, **{'args': ['git']})",
        "def launch(argv):\n subprocess.run(argv, shell=None)",
        "def launch(argv):\n subprocess.run(argv, executable=42)",
        "def launch(argv):\n subprocess.Popen(argv, check=False)",
        "def launch(argv):\n subprocess.call(argv, input=None)",
        "def launch(argv):\n subprocess.check_output(argv, check=False)",
        (
            "def launch(argv):\n launch=subprocess.run if flag else subprocess.Popen\n"
            " launch(argv, check=False)"
        ),
        "def launch(argv):\n subprocess.run(argv, -1, None, None, None, None, None, True, None)",
    ],
)
def test_formal_request_cannot_erase_unresolved_concrete_or_transformed_behavior(
    source: str,
) -> None:
    """A represented generic call cannot make an unsupported invocation disappear."""
    observed = reference_consumer_sources_from_files(
        {"src/example/probe.py": "import subprocess\n" + source}
    )

    assert "executable" in observed.unknown_consumers


def test_unmodeled_formal_mapping_access_cannot_claim_a_resolved_value() -> None:
    """A declared parameter is not evidence about its user-defined item behavior."""
    observed = reference_consumer_sources_from_files(
        {"src/example/probe.py": "import os\ndef read(config):\n os.getenv(config['name'])"}
    )

    assert "value" in observed.unknown_consumers


def test_formal_key_alternative_cannot_hide_an_invalid_literal() -> None:
    """A valid formal alternative cannot compensate for a concrete non-string key."""
    observed = reference_consumer_sources_from_files(
        {"src/example/probe.py": "import os\ndef read(key):\n os.getenv(key if flag else 3)"}
    )

    assert "value" in observed.unknown_consumers


def test_native_input_reader_preserves_repeated_formal_value() -> None:
    """A read-only native lookup does not mutate a possible key object between calls."""
    observed = reference_consumer_sources_from_files(
        {"src/example/probe.py": "import os\ndef read(key):\n os.getenv(key)\n os.getenv(key)"}
    )

    assert observed.unknown_consumers == {}
    assert len(observed.requests) == 2


def test_formal_request_keeps_a_known_default_as_a_possible_concrete_identity(
    tmp_path: Path,
) -> None:
    """A caller may omit the argument; its declared default still needs an owner."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import os\ndef read(name='UNDECLARED_INPUT'):\n os.getenv(name)",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [
        "semantic_consumer_orphan:value:UNDECLARED_INPUT:src/example/probe.py"
    ]
    assert report["requests"]


def test_concrete_native_call_keeps_its_unowned_identity_beside_the_formal_request(
    tmp_path: Path,
) -> None:
    """A parametric body does not exempt the actual selected executable."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\ndef launch(argv):\n subprocess.run(argv)\nlaunch(['probe-binary'])",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [
        "semantic_consumer_orphan:executable:probe-binary:src/example/probe.py"
    ]
    assert report["requests"]


def test_public_static_closure_reports_conditional_not_invocation_coverage(tmp_path: Path) -> None:
    """The static request contract never claims a dynamic runtime effect was verified."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\ndef launch(argv):\n subprocess.run(argv)",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "pass"
    assert report["coverage"] == "conditional"
    assert report["requests"]
    assert report["required_gaps"] == []


@pytest.mark.parametrize(
    "imports", ["from example.effects import launch", "from example.effects import launch as run"]
)
def test_current_caller_discharge_cannot_skip_a_first_party_formal_consumer(
    tmp_path: Path, imports: str
) -> None:
    """An imported effect owner still evaluates actual arguments at its native sink."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/effects.py",
        "import subprocess\ndef launch(argv):\n subprocess.run(argv)",
    )
    callable_name = "run" if " as run" in imports else "launch"
    write_reference_source(
        tmp_path,
        "src/example/use.py",
        f"{imports}\n{callable_name}(['probe-binary'])",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block"
    gaps = report["required_gaps"]
    assert isinstance(gaps, list)
    assert any(
        isinstance(gap, str) and "semantic_consumer_orphan:executable:probe-binary:" in gap
        for gap in gaps
    )


@pytest.mark.parametrize(
    ("source", "invocation"),
    [
        ("import subprocess\ndef launch(argv):\n subprocess.run(argv)", "external(launch)"),
        (
            (
                "from example.use import launch\nimport subprocess\n"
                "def launch(argv):\n subprocess.run(argv)"
            ),
            "launch(['probe-binary'])",
        ),
        ("import subprocess\ndef launch(argv):\n subprocess.run(argv)", "launch(compute())"),
        (
            "import subprocess\n@replacement\ndef launch(argv):\n subprocess.run(argv)",
            "launch(['probe-binary'])",
        ),
    ],
)
def test_unknown_first_party_call_or_escape_keeps_its_native_obligation(
    source: str, invocation: str
) -> None:
    """A callable's imported effects cannot disappear behind an unresolved consumer."""
    observed = reference_consumer_sources_from_files(
        {
            "src/example/effects.py": source,
            "src/example/use.py": "from example.effects import launch\n" + invocation,
        }
    )

    assert "executable" in observed.unknown_consumers


@pytest.mark.parametrize(
    "imports",
    [
        "import example.effects as effects",
        "import example.effects",
        "from . import effects",
        "from .effects import launch as effects",
    ],
)
def test_imported_first_party_binding_preserves_native_actual_values(imports: str) -> None:
    """Module aliases, relative imports and direct aliases use one source binding owner."""
    call = (
        "example.effects.launch"
        if imports == "import example.effects"
        else "effects"
        if "launch as" in imports
        else "effects.launch"
    )
    observed = reference_consumer_sources_from_files(
        {
            "src/example/effects.py": "import os\ndef launch(name):\n os.getenv(name)",
            "src/example/use.py": f"{imports}\n{call}('PROBE_INPUT')",
        }
    )

    assert set(observed.sources["value"]) == {"PROBE_INPUT"}
    assert observed.unknown_consumers == {}


@pytest.mark.parametrize("location", ["src/example/mutation.py", "src/example/use.py"])
def test_mutable_argument_write_cannot_be_lost_at_a_function_boundary(location: str) -> None:
    """Actual writes invalidate caller aliases even when a foreign function returns None."""
    source = "def mutate(argv):\n argv[0]='other-binary'\n return None"
    files = {location: source}
    files["src/example/use.py"] = (
        "import subprocess\n"
        + (
            source + "\n"
            if location.endswith("use.py")
            else "from example.mutation import mutate\n"
        )
        + "argv=['probe-binary']\nmutate(argv)\nsubprocess.run(argv)"
    )

    observed = reference_consumer_sources_from_files(files)

    assert "executable" in observed.unknown_consumers
    assert "probe-binary" not in observed.sources["executable"]


def test_ambiguous_first_party_module_retains_possible_native_consumers() -> None:
    """Colliding source roots cannot pick a definition or hide both effect obligations."""
    observed = reference_consumer_sources_from_files(
        {
            "src/example/effects.py": "import subprocess\ndef launch(argv):\n subprocess.run(argv)",
            "example/effects.py": "import os\ndef launch(name):\n os.getenv(name)",
            "src/example/use.py": "from example.effects import launch\nlaunch(['probe-binary'])",
        }
    )

    assert set(observed.unknown_consumers) == {"executable", "value"}


@pytest.mark.parametrize(
    "body",
    [
        "subprocess.Popen(['probe-binary'], check=False)",
        "def launch(argv):\n subprocess.run([argv, None])",
    ],
)
def test_invalid_known_native_alternative_is_not_a_formal_success(body: str) -> None:
    """Supported symbolic input cannot hide a concrete invalid native argument."""
    observed = reference_consumer_sources_from_files(
        {"src/example/use.py": "import subprocess\n" + body}
    )

    assert "executable" in observed.unknown_consumers


@pytest.mark.parametrize("cross_module", [False, True])
def test_analysis_bound_cannot_erase_a_later_native_invocation(*, cross_module: bool) -> None:
    """Work limits reduce precision, never turn an unobserved effect into success."""
    definition = "import subprocess\ndef launch(argv):\n subprocess.run(argv)"
    calls = "\n".join(["launch(['declared'])"] * 1030 + ["launch(['probe-binary'])"])
    files: dict[str, str] = (
        {
            "src/example/effects.py": definition,
            "src/example/use.py": "from example.effects import launch\n" + calls,
        }
        if cross_module
        else {"src/example/use.py": definition + "\n" + calls}
    )

    observed = reference_consumer_sources_from_files(files)

    assert (
        "probe-binary" in observed.sources["executable"]
        or "executable" in observed.unknown_consumers
    )


@pytest.mark.parametrize(
    "body",
    [
        (
            "def launch(argv, **options):\n"
            " subprocess.run(argv, **{**options, 'executable': 'probe-binary'})"
        ),
        "def launch(**options):\n subprocess.run(**{**options, 'args': ['probe-binary']})",
    ],
)
def test_open_formal_keyword_map_preserves_later_explicit_native_identity(body: str) -> None:
    """A symbolic remainder cannot erase a later override with a real ownership duty."""
    observed = reference_consumer_sources_from_files(
        {"src/example/use.py": "import subprocess\n" + body}
    )

    assert "probe-binary" in observed.sources["executable"]
    assert observed.requests


@pytest.mark.parametrize(
    ("body", "identities"),
    [
        (
            (
                "def launch(argv, **options):\n subprocess.run(argv, **("
                "{**options, 'executable': 'first'} if flag else "
                "{**options, 'executable': 'second'}))"
            ),
            {"first", "second"},
        ),
        (
            (
                "def launch(argv, **options):\n"
                " subprocess.run(argv, **{**options, 'args': ['second']})"
            ),
            set(),
        ),
    ],
)
def test_conditional_keyword_paths_keep_all_known_alternatives(
    body: str, identities: set[str]
) -> None:
    """Native binding cannot select one branch or certify a known duplicate argument."""
    observed = reference_consumer_sources_from_files(
        {"src/example/use.py": "import subprocess\n" + body}
    )

    assert set(observed.sources["executable"]) == identities
    if not identities:
        assert observed.requests == ()
        assert "executable" in observed.unknown_consumers


@pytest.mark.parametrize("attribute", ["'launch'", "operation"])
def test_first_party_getattr_retains_resolved_or_unknown_native_relation(attribute: str) -> None:
    """Dynamic attribute syntax must not bypass source-owned callable observation."""
    observed = reference_consumer_sources_from_files(
        {
            "src/example/effects.py": "import subprocess\ndef launch(argv):\n subprocess.run(argv)",
            "src/example/use.py": (
                "import example.effects as effects\n"
                f"getattr(effects, {attribute})(['probe-binary'])"
            ),
        }
    )

    if attribute == "'launch'":
        assert "probe-binary" in observed.sources["executable"]
    else:
        assert "executable" in observed.unknown_consumers


def test_unknown_decorated_local_consumer_cannot_become_conditional_success() -> None:
    """A decorator can replace or invoke the source body with unresolved inputs."""
    observed = reference_consumer_sources_from_files(
        {
            "src/example/use.py": (
                "import subprocess\n@replacement\ndef launch(argv):\n"
                " subprocess.run(argv)\nlaunch(['probe-binary'])"
            )
        }
    )

    assert "executable" in observed.unknown_consumers


@pytest.mark.parametrize("cross_module", [False, True])
def test_unmodeled_method_invocation_retains_its_native_obligation(*, cross_module: bool) -> None:
    """Deferred method requests cannot certify an unobserved actual instance call."""
    definition = (
        "import subprocess\nclass Effects:\n def launch(self, argv):\n  subprocess.run(argv)"
    )
    files: dict[str, str] = (
        {
            "src/example/effects.py": definition,
            "src/example/use.py": (
                "from example.effects import Effects\nEffects().launch(['probe-binary'])"
            ),
        }
        if cross_module
        else {"src/example/use.py": definition + "\nEffects().launch(['probe-binary'])"}
    )

    observed = reference_consumer_sources_from_files(files)

    assert "executable" in observed.unknown_consumers


def test_unresolved_star_import_keeps_a_source_native_consumer_relation() -> None:
    """Unsupported wildcard bindings remain related uncertainty, not absent effects."""
    observed = reference_consumer_sources_from_files(
        {
            "src/example/effects.py": "import subprocess\ndef launch(argv):\n subprocess.run(argv)",
            "src/example/use.py": "from example.effects import *\nlaunch(['probe-binary'])",
        }
    )

    assert "executable" in observed.unknown_consumers


def test_decorated_pure_function_does_not_inherit_unrelated_module_native_effects() -> None:
    """A module's unrelated import does not turn a source-owned no-op into an input reader."""
    observed = reference_consumer_sources_from_files(
        {"src/example/use.py": "import os\n@replacement\ndef noop():\n return None\nnoop()"}
    )

    assert observed.unknown_consumers == {}


def test_pure_analysis_limit_does_not_inherit_unrelated_native_imports() -> None:
    """Only the truncated callable's actual consumer relations require uncertainty."""
    source = "import subprocess\ndef pure():\n return 1\n" + "\n".join(["pure()"] * 1030)

    observed = reference_consumer_sources_from_files({"src/example/use.py": source})

    assert observed.unknown_consumers == {}
