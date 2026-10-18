"""Native orchestration of the repository paradigm.

Gates and CI steps run native tool commands or toolchain-owner tasks. A gate or step
that runs a tracked repository script is shell orchestration; a step, or a gate's
shell interpreter argument, that holds a shell program instead of one command is
inline shell. One command may continue its arguments over several lines, redirect its
output and quote any text; a Forge expression is resolved before the shell runs.
"""

from __future__ import annotations

import posixpath
import tomllib
from typing import TYPE_CHECKING

import yaml

from ethos.contracts.gates import GateRegistryDeclaration
from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.gap import tracked_text
from ethos.repository.paradigm.pipelines import forge_pipeline_files
from ethos.repository.paradigm.scripts import is_script
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Iterator
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import RepositoryParadigm

_CONTROL_WORDS = frozenset({"case", "for", "if", "select", "until", "while"})
_SHELLS = frozenset({"bash", "cmd", "dash", "ksh", "powershell", "pwsh", "sh", "zsh"})
_SHELL_PROGRAM_FLAGS = frozenset({"-c", "-Command", "/c", "/C"})
_GITLAB_STEPS = ("before_script", "script", "after_script")
_INLINE_REPAIR = (
    "make the step invoke one native command or toolchain-owner task; move a sequence into a "
    "task, environment into the Forge's variables and a directory change into its "
    "working-directory key"
)


class _ForgeLoader(yaml.SafeLoader):
    """Read Forge YAML, keeping a tagged node such as GitLab's !reference unread."""


_ForgeLoader.add_multi_constructor("!", lambda _loader, _suffix, _node: None)


def orchestration_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Report CI steps and gates that run repository scripts or hold shell programs."""
    scripts = sorted(path for path in tracked if is_script(paradigm, root, path))
    for forge, path in forge_pipeline_files(paradigm, tracked):
        for carrier, command in ci_steps(forge, path, tracked_text(root, path, tracked) or ""):
            yield from _command_gaps(carrier, command, scripts, inline=inline_shell(command))
    for carrier, command in _gate_commands(paradigm, root, tracked):
        inline = _shell_program(command)
        yield from _command_gaps(carrier, " ".join(command), scripts, inline=inline)


def ci_steps(forge: str, path: str, text: str) -> list[tuple[str, str]]:
    """Return each CI step of one Forge's pipeline file with a carrier naming its position."""
    reader = _STEP_READERS.get(forge)
    try:
        document = yaml.load(text, Loader=_ForgeLoader)
    except yaml.YAMLError:
        return []
    if reader is None or not isinstance(document, dict):
        return []
    return list(reader(path, document))


def inline_shell(command: str) -> bool:
    """Return whether one step's text is a shell program rather than one command."""
    text = command.replace("\\\n", " ")
    quote = ""
    index = 0
    while index < len(text):
        character = text[index]
        if quote == "'":
            quote = "" if character == "'" else quote
        elif character == "\\":
            index += 1
        elif character == "`" or text.startswith("$(", index):
            return True
        elif quote:
            quote = "" if character == '"' else quote
        elif character in "'\"":
            quote = character
        elif (skipped := _skipped(text, index)) is not None:
            index = skipped
        elif _separates(text, index):
            return True
        index += 1
    first = text.split(maxsplit=1)
    return bool(first) and first[0] in _CONTROL_WORDS


def _skipped(text: str, index: int) -> int | None:
    """Return where an unquoted Forge expression or comment ends, if one starts here."""
    if text.startswith("${{", index):
        end = text.find("}}", index)
        return len(text) if end < 0 else end + 1
    if text[index] == "#" and (index == 0 or text[index - 1].isspace()):
        end = text.find("\n", index)
        return len(text) if end < 0 else end - 1
    return None


def _separates(text: str, index: int) -> bool:
    """Return whether an unquoted character separates, chains or backgrounds commands."""
    character = text[index]
    if character in ";|" or (character == "&" and _background(text, index)):
        return True
    return character == "\n" and bool(text[index + 1 :].strip())


def _background(command: str, index: int) -> bool:
    """Return whether an ampersand chains or backgrounds commands, not redirects output."""
    before, after = command[index - 1 : index], command[index + 1 : index + 2]
    return after == "&" or (before not in "<>" and after != ">")


def _command_gaps(
    carrier: str, command: str, scripts: Iterable[str], *, inline: bool
) -> Iterator[ParadigmGap]:
    script = next((path for path in scripts if path in command), "")
    if script:
        yield ParadigmGap(
            "shell-orchestration",
            carrier,
            f"replace {script} with a native command or toolchain-owner task",
        )
    elif inline:
        yield ParadigmGap("inline-shell", carrier, _INLINE_REPAIR)


def _github_steps(path: str, document: dict[object, object]) -> Iterator[tuple[str, str]]:
    jobs = document.get("jobs")
    for job, body in jobs.items() if isinstance(jobs, dict) else ():
        steps = body.get("steps") if isinstance(body, dict) else None
        for index, step in enumerate(steps if isinstance(steps, list) else ()):
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                yield f"{path}:jobs.{job}.steps[{index}]", step["run"]


def _gitlab_steps(path: str, document: dict[object, object]) -> Iterator[tuple[str, str]]:
    for job, body in document.items():
        if not isinstance(body, dict):
            continue
        for key in _GITLAB_STEPS:
            entries = body.get(key)
            listed = [entries] if isinstance(entries, str) else entries
            for index, entry in enumerate(listed if isinstance(listed, list) else ()):
                if isinstance(entry, str):
                    yield f"{path}:{job}.{key}[{index}]", entry


_STEP_READERS = {"github": _github_steps, "gitlab": _gitlab_steps}


def _gate_commands(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[tuple[str, tuple[str, ...]]]:
    """Return the command of every declared gate, from the profile or its gate registry."""
    declaration = load_repository_profile(root).declaration
    proof = declaration.proof if declaration else None
    if proof is None:
        return
    profile = f"{paradigm.binding.root}/profile.toml"
    for gate in proof.gates:
        yield f"{profile}:proof.gates.{gate.id}", tuple(gate.command)
    registry = proof.gate_registry
    text = tracked_text(root, registry, tracked) if registry else None
    if text is None:
        return
    try:
        declared = GateRegistryDeclaration.model_validate(tomllib.loads(text))
    except ValueError:
        return  # The gate registry owner reports an unreadable or invalid registry.
    for gate in declared.gates:
        yield f"{registry}:gates.{gate.id}", tuple(gate.command)


def _shell_program(command: tuple[str, ...]) -> bool:
    """Return whether a gate hands a program to a shell interpreter."""
    return (
        bool(command)
        and posixpath.basename(command[0]) in _SHELLS
        and any(word in _SHELL_PROGRAM_FLAGS for word in command[1:])
    )
