"""Observe product references carried by Markdown documents."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

from markdown_it import MarkdownIt

import ethos.repository.policy.references.commands as command_references

if TYPE_CHECKING:
    from collections.abc import Callable

    from markdown_it.token import Token


def markdown_references(
    path: str,
    text: str,
    known_commands: command_references.CommandVocabulary,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
    *,
    yaml_references: Callable[
        [str, str, dict[str, set[str]], dict[str, set[str]]],
        bool,
    ],
) -> bool:
    """Observe commands and executables from one Markdown carrier."""
    require_declared = _requires_declared_commands(path)
    tokens = markdown_tokens(text)
    if tokens is None:
        return False
    removed_section = False
    scenario = False
    openspec = path.startswith(("openspec/specs/", "openspec/changes/"))
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag in {"h2", "h3", "h4"}:
            heading = tokens[index + 1].content if index + 1 < len(tokens) else ""
            if token.tag == "h2":
                removed_section = heading.strip() == "REMOVED Requirements"
                scenario = False
            elif token.tag == "h3":
                scenario = False
            elif token.tag == "h4":
                scenario = heading.startswith("Scenario:")
            continue
        if removed_section:
            continue
        _update_fence_references(
            path=path,
            token=token,
            known_commands=known_commands,
            npm_scripts=npm_scripts,
            observed=observed,
            require_declared=require_declared,
            yaml_references=yaml_references,
        )
        if token.type != "inline" or not token.children or (openspec and not scenario):
            continue
        _update_inline_references(
            children=token.children,
            openspec=openspec,
            known_commands=known_commands,
            npm_scripts=npm_scripts,
            observed=observed,
            require_declared=require_declared,
        )
    return True


def markdown_tokens(text: str) -> tuple[Token, ...] | None:
    """Parse one Markdown carrier, preserving parser failure as unknown."""
    try:
        return tuple(_MARKDOWN.parse(text))
    except RuntimeError:
        return None


def _update_fence_references(
    *,
    path: str,
    token: Token,
    known_commands: command_references.CommandVocabulary,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
    require_declared: bool,
    yaml_references: Callable[
        [str, str, dict[str, set[str]], dict[str, set[str]]],
        bool,
    ],
) -> None:
    if token.type != "fence":
        return
    language = token.info.partition(" ")[0].lower()
    if language in {"yaml", "yml"}:
        yaml_references(path, token.content, npm_scripts, observed)
        return
    if language not in {"bash", "console", "sh", "shell", "zsh"}:
        return
    shell = (
        "\n".join(
            line.lstrip()[2:]
            for line in token.content.splitlines()
            if line.lstrip().startswith(("$ ", "> "))
        )
        if language == "console"
        else token.content
    )
    observed["executable"].update(command_references.shell_executables(shell, npm_scripts))
    observed["command"].update(
        command_references.shell_commands(
            shell,
            known_commands,
            require_declared=require_declared,
        )
    )


def _update_inline_references(
    *,
    children: list[Token],
    openspec: bool,
    known_commands: command_references.CommandVocabulary,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
    require_declared: bool,
) -> None:
    inline_codes = (
        _openspec_scenario_commands(children)
        if openspec
        else tuple(child.content for child in children if child.type == "code_inline")
    )
    for inline in inline_codes:
        _record_inline_command(
            inline,
            known_commands=known_commands,
            npm_scripts=npm_scripts,
            observed=observed,
            require_declared=require_declared,
        )


def _openspec_scenario_commands(children: list[Token]) -> tuple[str, ...]:
    """Return direct GIVEN/WHEN command subjects, not mentioned negative examples."""
    marker = ""
    before_code = ""
    in_strong = False
    strong_text = ""
    commands: list[str] = []
    for child in children:
        if child.type == "strong_open":
            in_strong = True
            strong_text = ""
        elif child.type == "strong_close":
            in_strong = False
            if strong_text.strip() in {"GIVEN", "WHEN"}:
                marker = strong_text.strip()
                before_code = ""
        elif child.type == "text":
            if in_strong:
                strong_text += child.content
            elif marker:
                before_code += child.content
        elif child.type == "code_inline" and marker and not before_code.strip():
            commands.append(child.content)
            marker = ""
    return tuple(commands)


def _record_inline_command(
    inline: str,
    *,
    known_commands: command_references.CommandVocabulary,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
    require_declared: bool,
) -> None:
    try:
        tokens = tuple(shlex.split(inline))
    except ValueError:
        return
    if command := command_references.command_identity(
        tokens,
        known_commands,
        require_declared=require_declared,
    ):
        observed["command"].add(command)
        observed["executable"].update(command_references.command_executables(tokens, npm_scripts))


def _requires_declared_commands(path: str) -> bool:
    if path in {"AGENTS.md", "CONTRIBUTING.md", "README.md", "docs/README.md"}:
        return True
    return path.startswith(
        (
            ".agents/skills/",
            ".config/forge/",
            ".github/ISSUE_TEMPLATE/",
            ".gitlab/issue_templates/",
            "docs/architecture/",
            "docs/concepts/",
            "docs/governance/",
            "docs/reference/",
            "docs/guides/",
            "openspec/changes/",
            "openspec/specs/",
            "rules/",
        )
    )


_MARKDOWN = MarkdownIt("commonmark")
