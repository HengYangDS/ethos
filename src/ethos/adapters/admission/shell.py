from __future__ import annotations

import shlex

from ethos.contracts.branch.roles import PROTECTED_WRITE_ROLES


def _words(text: str) -> frozenset[str]:
    return frozenset(text.split())


_MUTATION_PATTERNS = (
    " write_text(",
    ".write_text(",
    " >",
    ">>",
    " tee ",
    "sed -i",
    "python -c",
    "rm ",
    "mv ",
    "cp ",
)
_GIT_READ_SUBCOMMANDS = _words(
    "blame branch diff grep log ls-files merge-base rev-list rev-parse show show-ref status "
    "tag worktree"
)
_GIT_MUTATION_SUBCOMMANDS = _words(
    "add am apply branch checkout cherry-pick clean commit merge mv pull push rebase reset "
    "restore revert rm stash switch update-ref"
)
_SHELL_MUTATION_COMMANDS = _words(
    "chmod chown cp install mkdir mv patch rm rmdir rsync sed tee touch truncate"
)
_PROTECTED_READ_COMMANDS = _words("cat find grep head less ls pwd rg tail tree wc")
_ETHOS_READ_COMMANDS = _words("audit openspec plan playbooks quality status")
_BRANCH_MUTATION_FLAGS = _words("-d -D -m -M -c -C -f --delete --move --copy --force")
_BRANCH_VALUE_FLAGS = _words("--format --color --sort --points-at")


def command_risk(command: str, *, role: str) -> dict[str, object]:
    stripped = command.strip()
    lowered = f" {stripped.lower()} "
    pattern_risky = any(pattern in lowered for pattern in _MUTATION_PATTERNS)
    tokens = _shell_tokens(stripped)
    explicit_mutation = _has_explicit_mutation_command(tokens)
    if pattern_risky or explicit_mutation:
        return _risk(risky=True, reason="command_text_matches_mutation_pattern")
    if role in PROTECTED_WRITE_ROLES and stripped and not _is_protected_read_command(tokens):
        return _risk(risky=True, reason="protected_role_unknown_command_requires_paths")
    return _risk(risky=False, reason="observe_only_command")


def _risk(*, risky: bool, reason: str) -> dict[str, object]:
    return {"tracked_mutation_risk": risky, "reason": reason}


def _has_explicit_mutation_command(tokens: list[str]) -> bool:
    if not tokens:
        return False
    for index, token in enumerate(tokens):
        command = _command_name(token)
        if command in _SHELL_MUTATION_COMMANDS:
            return True
        if command != "git":
            continue
        subcommand_index = _find_git_subcommand(tokens, start=index + 1)
        if subcommand_index is None:
            continue
        subcommand = tokens[subcommand_index]
        if subcommand == "stash" and _git_stash_operation(tokens) in {"list", "show"}:
            continue
        if subcommand == "branch" and _git_branch_is_read_only(tokens[subcommand_index + 1 :]):
            continue
        if subcommand == "worktree" and _git_worktree_is_read_only(tokens[subcommand_index + 1 :]):
            continue
        if subcommand in _GIT_MUTATION_SUBCOMMANDS:
            return True
    return False


def _is_protected_read_command(tokens: list[str]) -> bool:
    if not tokens:
        return True
    first = _command_name(tokens[0])
    if first in _PROTECTED_READ_COMMANDS:
        return True
    if first == "git":
        return _git_command_is_read_only(tokens)
    if first == "ethos":
        return _ethos_command_is_read_only(tokens)
    return False


def _git_command_is_read_only(tokens: list[str]) -> bool:
    subcommand_index = _find_git_subcommand(tokens, start=1)
    if subcommand_index is None:
        return False
    subcommand = tokens[subcommand_index]
    if subcommand == "stash":
        return _git_stash_operation(tokens) in {"list", "show"}
    if subcommand == "branch":
        return _git_branch_is_read_only(tokens[subcommand_index + 1 :])
    if subcommand == "worktree":
        return _git_worktree_is_read_only(tokens[subcommand_index + 1 :])
    return subcommand in _GIT_READ_SUBCOMMANDS


def _ethos_command_is_read_only(tokens: list[str]) -> bool:
    subcommand = _first_non_option(tokens[1:])
    return subcommand in _ETHOS_READ_COMMANDS


def _git_branch_is_read_only(args: list[str]) -> bool:
    index = 0
    while index < len(args):
        arg = args[index]
        if (
            arg == "--"
            or arg in _BRANCH_MUTATION_FLAGS
            or arg.startswith(("--set-upstream", "--unset-upstream"))
        ):
            return False
        if not arg.startswith("-"):
            return False
        index += 2 if arg in _BRANCH_VALUE_FLAGS else 1
    return True


def _git_worktree_is_read_only(args: list[str]) -> bool:
    subcommand = _first_non_option(args)
    return subcommand == "list" if subcommand else True


def _first_non_option(tokens: list[str]) -> str | None:
    for argument in tokens:
        if not argument.startswith("-"):
            return argument
    return None


def _command_name(argument: str) -> str:
    return argument.rsplit("/", maxsplit=1)[-1].lower()


def git_stash_policy(command: str) -> dict[str, object]:
    tokens = _shell_tokens(command)
    operation = _git_stash_operation(tokens)
    if operation is None:
        return _stash(forbidden=False, operation="", reason="not_git_stash")
    if operation in {"list", "show"}:
        return _stash(forbidden=False, operation=operation, reason="observe_only_stash_read")
    return _stash(forbidden=True, operation=operation, reason="stash_is_hidden_change_carrier")


def _stash(*, forbidden: bool, operation: str, reason: str) -> dict[str, object]:
    return {"forbidden": forbidden, "operation": operation, "reason": reason}


def _shell_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def _git_stash_operation(tokens: list[str]) -> str | None:
    for index, argument in enumerate(tokens):
        if argument != "git":
            continue
        stash_index = _find_git_subcommand(tokens, start=index + 1)
        if stash_index is None or tokens[stash_index] != "stash":
            continue
        if stash_index + 1 >= len(tokens) or tokens[stash_index + 1].startswith("-"):
            return "push"
        return tokens[stash_index + 1]
    return None


def _find_git_subcommand(tokens: list[str], *, start: int) -> int | None:
    index = start
    while index < len(tokens):
        argument = tokens[index]
        if argument in {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}:
            index += 2
            continue
        if argument.startswith(("--git-dir=", "--work-tree=", "--namespace=", "--exec-path=")):
            index += 1
            continue
        if argument.startswith("-"):
            index += 1
            continue
        return index
    return None
