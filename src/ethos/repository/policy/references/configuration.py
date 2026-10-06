"""Native YAML reference observation with explicit acyclic alias coverage."""

from __future__ import annotations

import yaml

from ethos.repository.policy.references.commands.invocation import shell_executables


def yaml_references(
    path: str,
    text: str,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
) -> bool:
    """Read shared YAML nodes once; cycles remain unsupported, not silently evaluated."""
    provider = (
        "github"
        if path.startswith(".github/")
        else "gitlab"
        if path == ".gitlab-ci.yml" or path.startswith(".gitlab/")
        else None
    )
    if provider is not None:
        observed["reference"].add(provider)
    try:
        root = yaml.safe_load(text)
    except (yaml.YAMLError, RecursionError):
        return False
    active: set[int] = set()
    visited: set[int] = set()
    stack = [(root, False)]
    while stack:
        value, finished = stack.pop()
        if not isinstance(value, list | dict):
            continue
        identity = id(value)
        if finished:
            active.remove(identity)
            visited.add(identity)
        elif identity in active:
            return False
        elif identity not in visited:
            active.add(identity)
            stack.append((value, True))
            children = value if isinstance(value, list) else list(value.values())
            stack.extend((child, False) for child in reversed(children))
            if isinstance(value, dict):
                for key, item in value.items():
                    configuration_reference(str(key), item, npm_scripts, observed)
    return True


def configuration_reference(
    key: str,
    item: object,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
) -> None:
    """Consume declared workflow effect fields, never arbitrary scalar appearance."""
    if key == "uses" and isinstance(item, str):
        if reference := github_reference(item):
            observed["reference"].add(reference)
    elif key in {"run", "script"}:
        commands = item if isinstance(item, list) else [item]
        for command in commands:
            if isinstance(command, str):
                observed["executable"].update(
                    shell_executables(command, npm_scripts, module_imports=observed["import"])
                )
    elif key == "image" and isinstance(item, str) and item:
        observed["reference"].add("docker")


def github_reference(value: str) -> str:
    """Distinguish local actions and container carriers from Forge-owned references."""
    action = value.strip().strip("'\"")
    if not action or action.startswith("./"):
        return ""
    if action.startswith("docker://"):
        return "docker"
    return "github" if "@" in action and "/" in action.partition("@")[0] else ""
