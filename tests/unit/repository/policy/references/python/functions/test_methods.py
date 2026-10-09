"""Qualify actual source receivers through the public reference consumers."""

from __future__ import annotations

from pathlib import Path

import pytest

from ethos.repository.policy.references.closure import repository_semantic_closure
from ethos.repository.policy.references.observation import product_references_from_files
from tests.support.architecture import declare_reference_package
from tests.support.architecture import declare_reference_surface
from tests.support.architecture import write_reference_source


@pytest.mark.parametrize("access", ["direct", "saved", "imported"])
def test_public_closure_binds_plain_source_method(tmp_path: Path, access: str) -> None:
    """A proven instance call retains the same executable as its function body."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    owner = (
        "import subprocess\n"
        "class Scope:\n"
        "    def start(self, command):\n"
        "        return subprocess.Popen(command)\n"
    )
    calls = {
        "direct": 'Scope().start(("source_method_probe",))\n',
        "saved": 'scope = Scope()\nstart = scope.start\nstart(("source_method_probe",))\n',
        "imported": ('from example.scope import Scope\nScope().start(("source_method_probe",))\n'),
    }
    if access == "imported":
        write_reference_source(tmp_path, "src/example/scope.py", owner)
        owner = ""
    write_reference_source(tmp_path, "src/example/probe.py", owner + calls[access])

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block", report
    assert {item["identity"] for item in report["orphan"]} == {"source_method_probe"}, report


def test_public_closure_keeps_instance_fields_distinct(tmp_path: Path) -> None:
    """Initializer fields and later writes belong to the actual allocation and aliases."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Scope:\n"
        "    def __init__(self, command):\n"
        "        self.command = command\n"
        "    def start(self):\n"
        "        return subprocess.Popen(self.command)\n"
        'first = Scope(("first_method_probe",))\n'
        'second = Scope(("second_method_probe",))\n'
        "alias = first\n"
        'alias.command = ("updated_method_probe",)\n'
        "first.start()\nsecond.start()\n",
    )

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block", report
    assert {item["identity"] for item in report["orphan"]} == {
        "updated_method_probe",
        "second_method_probe",
    }, report


def test_public_closure_keeps_lookup_time_method_binding(tmp_path: Path) -> None:
    """Replacing a later instance member cannot erase an already bound function."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Scope:\n"
        "    def start(self, command):\n"
        "        return subprocess.Popen(command)\n"
        "scope = Scope()\nsaved = scope.start\n"
        "scope.start = lambda command: None\n"
        'saved(("saved_method_probe",))\n'
        'scope.start(("unused_method_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block", report
    assert {item["identity"] for item in report["orphan"]} == {"saved_method_probe"}, report


@pytest.mark.parametrize("receiver", ["Scope", "Scope()"])
def test_public_closure_keeps_static_method_signature(tmp_path: Path, receiver: str) -> None:
    """A native staticmethod binds no instance argument through either access route."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Scope:\n"
        "    @staticmethod\n"
        "    def start(command):\n"
        "        return subprocess.Popen(command)\n"
        f'{receiver}.start(("static_method_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block", report
    assert {item["identity"] for item in report["orphan"]} == {"static_method_probe"}, report


def test_actual_git_wrapper_exposes_native_executable() -> None:
    """The actual process owner remains visible without closing dynamic input families."""
    root = Path(__file__).resolve().parents[7]
    paths = ("src/ethos/adapters/process.py", "src/ethos/adapters/repo/git.py")
    context = {path: (root / path).read_text(encoding="utf-8") for path in paths}
    source = (
        "from pathlib import Path\n"
        "from ethos.adapters.repo.git import run_git\n"
        'run_git(Path("."), "rev-parse", "HEAD", observation=True)\n'
    )

    observed = product_references_from_files(
        {"src/actual_git_probe.py": source},
        context_files=context,
        include_declarations=False,
    )

    assert observed.references["executable"] == {"git"}, observed
    assert {"GIT_CONFIG_COUNT", "PATH"} <= observed.references["value"], observed
    assert {(item.kind, item.state, item.target) for item in observed.uncertainties} >= {
        ("value", "unknown", "os.environ.__getitem__")
    }, observed
    assert not any(
        item.kind == "executable" and item.state == "unknown" and item.target == "subprocess.Popen"
        for item in observed.uncertainties
    ), observed
    assert {
        (item.path, item.reason)
        for item in observed.uncertainties
        if item.kind == "executable" and item.state == "unknown"
    } <= {("src/ethos/adapters/process.py", "opaque_capability_escape")}, observed


def test_public_closure_never_inherits_module_members_into_a_class(tmp_path: Path) -> None:
    """Native class lookup cannot fall through to a similarly named global function."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "def start(command):\n"
        "    return subprocess.Popen(command)\n"
        "class Scope:\n"
        "    pass\n"
        'Scope().start(("unused_global_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert not report["orphan"], report


def test_public_closure_binds_a_function_assigned_to_the_class(tmp_path: Path) -> None:
    """A class-written source function is a descriptor; an instance-written function is not."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Scope:\n"
        "    pass\n"
        "def start(self, command):\n"
        "    return subprocess.Popen(command)\n"
        "Scope.start = start\n"
        'Scope().start(("class_written_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert {item["identity"] for item in report["orphan"]} == {"class_written_probe"}, report


def test_public_closure_reads_current_class_method_at_each_call(tmp_path: Path) -> None:
    """A helper's cached source relation cannot freeze a mutable class namespace."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Scope:\n"
        "    def start(self, command):\n"
        "        return subprocess.Popen(command)\n"
        "def quiet(self, command):\n"
        "    return None\n"
        "def launch(command):\n"
        "    Scope().start(command)\n"
        'launch(("initial_class_probe",))\n'
        "Scope.start = quiet\n"
        'launch(("unused_class_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert {item["identity"] for item in report["orphan"]} == {"initial_class_probe"}, report


@pytest.mark.parametrize("alternative", ["Scope", "scope.start", "quiet", "Scope()"])
@pytest.mark.parametrize("after_store", ["", "Scope.start = later\n"])
def test_public_closure_preserves_unselected_instance_lookup(
    tmp_path: Path, alternative: str, after_store: str
) -> None:
    """A may-store retains both field presence and later class lookup on the unselected path."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Scope:\n"
        "    def start(self, command):\n"
        "        return subprocess.Popen(command)\n"
        "def quiet(command):\n"
        "    return None\n"
        "def later(self, command):\n"
        '    return subprocess.Popen((command[0] + "_later",))\n'
        "scope = Scope()\n"
        f"selected = scope if condition else {alternative}\n"
        "selected.start = quiet\n"
        + after_store
        + 'scope.start(("unselected_instance_lookup_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    expected = "unselected_instance_lookup_probe" + ("_later" if after_store else "")
    assert {item["identity"] for item in report["orphan"]} == {expected}, report
    assert report["verdict"] != "pass", report


@pytest.mark.parametrize(
    "change",
    [
        "Scope.__getattribute__ = external_lookup\n",
        "Scope.__getattr__ = external_lookup\n",
        "Scope.__new__ = external_constructor\n",
        "Scope.__bases__ = external_bases\n",
        "Scope.start = external_descriptor\n",
    ],
)
def test_public_closure_keeps_changed_class_lookup_unknown(tmp_path: Path, change: str) -> None:
    """Native instance lookup needs current class authority, not its definition-time shape."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Scope:\n"
        "    def start(self, command):\n"
        "        return subprocess.Popen(command)\n"
        f"{change}"
        'Scope().start(("changed_lookup_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "unknown", report
    assert report["verdict"] != "pass", report


@pytest.mark.parametrize("escaped", ["scope", "Scope", "[scope]"])
def test_public_closure_keeps_escaped_class_authority_unknown(tmp_path: Path, escaped: str) -> None:
    """Opaque transfer can change a receiver or its class before the next member lookup."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Scope:\n"
        "    def start(self, command):\n"
        "        return subprocess.Popen(command)\n"
        "scope = Scope()\n"
        f"external({escaped})\n"
        'scope.start(("escaped_lookup_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "unknown", report
    assert report["verdict"] != "pass", report


def test_public_closure_preserves_saved_method_through_class_lookup_change(tmp_path: Path) -> None:
    """A bound function's saved identity survives a later change to class lookup."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Scope:\n"
        "    def start(self, command):\n"
        "        return subprocess.Popen(command)\n"
        "scope = Scope()\n"
        "start = scope.start\n"
        "Scope.__getattribute__ = external_lookup\n"
        'start(("saved_lookup_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert {item["identity"] for item in report["orphan"]} == {"saved_lookup_probe"}, report
    assert report["coverage"] != "unknown", report


@pytest.mark.parametrize("access", ["direct", "imported", "reexported"])
def test_public_closure_replaces_one_source_class_member(tmp_path: Path, access: str) -> None:
    """One exact imported class store replaces its live method, not a stale export."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    owner = (
        "import subprocess\n"
        "class Scope:\n"
        "    def start(self, command):\n"
        "        return subprocess.Popen(command)\n"
        "def quiet(self, command):\n"
        '    return subprocess.Popen(("replacement_class_probe",))\n'
    )
    if access != "direct":
        write_reference_source(tmp_path, "src/example/scope.py", owner)
        owner = "from example.scope import Scope, quiet\n"
        if access == "reexported":
            write_reference_source(tmp_path, "src/example/exports.py", owner)
            owner = "from example.exports import Scope, quiet\n"
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        owner + "Scope.start = quiet\n" + 'Scope().start(("replaced_class_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert {item["identity"] for item in report["orphan"]} == {"replacement_class_probe"}, report
    assert report["coverage"] != "unknown", report


@pytest.mark.parametrize("member", ["function", "non_data_descriptor"])
def test_public_closure_preserves_native_instance_field_precedence(
    tmp_path: Path, member: str
) -> None:
    """A closed non-data descriptor still permits an unbound instance-written callable."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    declaration = (
        "class Scope:\n    def start(self, command):\n        return subprocess.Popen(command)\n"
        if member == "function"
        else "class Descriptor:\n"
        "    def __get__(self, instance, owner):\n"
        "        return subprocess.Popen\n"
        "class Scope:\n"
        "    start = Descriptor()\n"
    )
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n" + declaration + "def quiet(command):\n"
        "    return None\n"
        "scope = Scope()\n"
        "scope.start = quiet\n"
        'scope.start(("unused_descriptor_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert not report["orphan"], report
    assert report["coverage"] != "unknown", report


@pytest.mark.parametrize("access", ["direct", "captured", "imported"])
def test_public_closure_keeps_unselected_class_store_alternatives(
    tmp_path: Path, access: str
) -> None:
    """A write through two possible classes cannot replace both original members."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    owner = (
        "import subprocess\n"
        "class Scope:\n"
        "    def start(self, command):\n"
        "        return subprocess.Popen(command)\n"
        "class Other:\n"
        "    def start(self, command):\n"
        "        return None\n"
        "def quiet(self, command):\n"
        "    return None\n"
    )
    prefix = ""
    if access == "imported":
        write_reference_source(tmp_path, "src/example/scope.py", owner)
        owner = ""
        prefix = "from example.scope import Scope, Other, quiet\n"
    change = (
        "def replace_selected():\n    selected.start = quiet\nreplace_selected()\n"
        if access == "captured"
        else "selected.start = quiet\n"
    )
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        owner
        + prefix
        + "selected = Scope if condition else Other\n"
        + change
        + 'Scope().start(("unselected_class_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert {item["identity"] for item in report["orphan"]} == {"unselected_class_probe"}, report
    assert report["coverage"] != "unknown", report


@pytest.mark.parametrize("owner", ["scope.start", "scope"])
def test_public_closure_class_store_preserves_nonclass_owner_alternatives(
    tmp_path: Path, owner: str
) -> None:
    """One class alternative is not a unique store owner when a callable or instance survives."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Scope:\n"
        "    def start(self, command):\n"
        "        return subprocess.Popen(command)\n"
        "def quiet(self, command):\n"
        "    return None\n"
        "scope = Scope()\n"
        f"selected = Scope if condition else {owner}\n"
        "selected.start = quiet\n"
        'Scope().start(("nonclass_owner_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert {item["identity"] for item in report["orphan"]} == {"nonclass_owner_probe"}, report


@pytest.mark.parametrize(
    "change",
    [
        "scope.__class__ = Other\n",
        "Scope.__getattribute__ = external_lookup\n",
        "Scope.start = external_descriptor\n",
        "Scope.__setattr__ = external_store\nscope.start = quiet\n",
    ],
)
def test_public_closure_keeps_instance_field_dispatch_authority_unknown(
    tmp_path: Path, change: str
) -> None:
    """An instance field cannot bypass changed class lookup or custom store behavior."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Scope:\n"
        "    def start(self, command):\n"
        "        return subprocess.Popen(command)\n"
        "class Other:\n"
        "    def start(self, command):\n"
        "        return None\n"
        "def quiet(command):\n"
        "    return None\n"
        "scope = Scope()\n"
        "scope.start = quiet\n"
        f"{change}"
        'scope.start(("changed_instance_field_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "unknown", report
    assert report["verdict"] != "pass", report


def test_public_closure_keeps_data_descriptor_store_unknown(tmp_path: Path) -> None:
    """An ordinary field assignment does not replace a possible data descriptor."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Descriptor:\n"
        "    def __get__(self, instance, owner):\n"
        "        return subprocess.run\n"
        "    def __set__(self, instance, value):\n"
        "        pass\n"
        "class Scope:\n"
        "    start = Descriptor()\n"
        "def quiet(command):\n"
        "    return None\n"
        "scope = Scope()\n"
        "scope.start = quiet\n"
        'scope.start(("data_descriptor_probe",))\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "unknown", report
    assert report["verdict"] != "pass", report
