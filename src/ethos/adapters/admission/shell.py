from __future__ import annotations

import shlex

from ethos.contracts.admission import ethos_command_is_readonly

_SHELL_OPERATORS = frozenset({"&", "&&", ";", "<", "<<", ">", ">>", "|", "||"})
_MUTATION_TOKENS = frozenset(
    {
        "-delete",
        "-exec",
        "-execdir",
        "-ok",
        "-okdir",
        "chmod",
        "chown",
        "cp",
        "install",
        "mkdir",
        "mv",
        "patch",
        "rm",
        "rmdir",
        "rsync",
        "sed",
        "tee",
        "touch",
        "truncate",
    }
)
_READ_COMMANDS = frozenset(
    {"cat", "find", "grep", "head", "less", "ls", "pwd", "rg", "tail", "tree", "wc"}
)
_GIT_READ_SUBCOMMANDS = frozenset(
    {
        "blame",
        "diff",
        "grep",
        "log",
        "ls-files",
        "merge-base",
        "rev-list",
        "rev-parse",
        "show",
        "show-ref",
        "status",
    }
)
_GIT_GLOBAL_VALUE_OPTIONS = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace"})
_GIT_GLOBAL_FLAGS = frozenset(
    {
        "-p",
        "-P",
        "--paginate",
        "--no-pager",
        "--no-replace-objects",
        "--bare",
        "--literal-pathspecs",
        "--glob-pathspecs",
        "--noglob-pathspecs",
        "--icase-pathspecs",
        "--no-optional-locks",
    }
)
_BRANCH_LIST_FLAGS = frozenset({"-l", "--list"})
_BRANCH_READ_FLAGS = frozenset(
    {
        "-a",
        "--all",
        "-r",
        "--remotes",
        "-v",
        "-vv",
        "--verbose",
        "--no-abbrev",
        "--column",
        "--no-column",
        "--ignore-case",
        "--show-current",
    }
)
_BRANCH_REQUIRED_VALUE_OPTIONS = frozenset({"--format", "--sort", "--points-at"})
_BRANCH_QUERY_OPTIONS = frozenset({"--contains", "--no-contains", "--merged", "--no-merged"})
_BRANCH_ASSIGNMENT_OPTIONS = frozenset({"--color", "--abbrev"})
_TAG_LIST_FLAGS = frozenset({"-l", "--list"})
_TAG_VERIFY_FLAGS = frozenset({"-v", "--verify"})
_TAG_READ_FLAGS = frozenset({"--ignore-case", "--no-column", "--omit-empty"})
_TAG_REQUIRED_VALUE_OPTIONS = frozenset({"--format", "--sort", "--points-at"})
_TAG_QUERY_OPTIONS = frozenset({"--contains", "--no-contains", "--merged", "--no-merged"})
_TAG_ASSIGNMENT_OPTIONS = frozenset({"--color", "--column"})
_COMMAND_PREFIXES = frozenset({"command", "sudo"})


def command_risk(command: str) -> dict[str, object]:
    """Classify unknown or effect-capable shell text as tracked-mutation risk."""
    stripped = command.strip()
    tokens, unsupported = _shell_tokens(stripped)
    if unsupported:
        return {
            "tracked_mutation_risk": True,
            "unclassifiable": True,
            "reason": unsupported,
        }
    if any(token in _SHELL_OPERATORS for token in tokens):
        return {
            "tracked_mutation_risk": True,
            "unclassifiable": True,
            "reason": "shell_composition_unsupported",
        }
    risky = bool(stripped) and (
        any(_command_name(token) in _MUTATION_TOKENS for token in tokens)
        or not _command_is_readonly(tokens)
    )
    return {
        "tracked_mutation_risk": risky,
        "unclassifiable": False,
        "reason": "command_text_matches_mutation_pattern" if risky else "observe_only_command",
    }


def git_stash_policy(command: str) -> dict[str, object]:
    """Forbid every Git stash effect while retaining list/show observation."""
    tokens, unsupported = _shell_tokens(command)
    invocation = None if unsupported else _git_invocation(_unwrapped_command(tokens))
    operation = _stash_operation(invocation[1]) if invocation and invocation[0] == "stash" else None
    allowed = operation in {None, "list", "show"}
    return {
        "forbidden": not allowed,
        "operation": operation or "",
        "reason": (
            "not_git_stash"
            if operation is None
            else "observe_only_stash_read"
            if allowed
            else "stash_is_hidden_change_carrier"
        ),
    }


def _command_is_readonly(tokens: list[str]) -> bool:
    tokens = _unwrapped_command(tokens)
    if not tokens:
        return True
    command = _command_name(tokens[0])
    if command == "git":
        return _git_command_is_readonly(tokens)
    if command == "ethos":
        return ethos_command_is_readonly(tokens)
    return command in _READ_COMMANDS


def _unwrapped_command(tokens: list[str]) -> list[str]:
    """Remove standard command wrappers before classifying the invoked program."""
    index = 0
    while index < len(tokens):
        command = _command_name(tokens[index])
        if command in _COMMAND_PREFIXES:
            index += 1
        elif command == "env":
            index += 1
            while (
                index < len(tokens) and "=" in tokens[index] and not tokens[index].startswith("=")
            ):
                index += 1
        else:
            break
    return tokens[index:]


def _git_command_is_readonly(tokens: list[str]) -> bool:
    invocation = _git_invocation(tokens)
    if invocation is None:
        return False
    subcommand, arguments = invocation
    if subcommand == "stash":
        return _stash_operation(arguments) in {"list", "show"}
    if subcommand == "branch":
        return _git_branch_is_readonly(arguments)
    if subcommand == "tag":
        return _git_tag_is_readonly(arguments)
    if subcommand == "worktree":
        return next((item for item in arguments if not item.startswith("-")), "list") == "list"
    return subcommand in _GIT_READ_SUBCOMMANDS


def _git_branch_is_readonly(arguments: list[str]) -> bool:
    return _git_selector_is_readonly(
        arguments,
        positional_modes=_BRANCH_LIST_FLAGS,
        flags=_BRANCH_READ_FLAGS,
        required_values=_BRANCH_REQUIRED_VALUE_OPTIONS,
        query_values=_BRANCH_QUERY_OPTIONS,
        assignment_options=_BRANCH_ASSIGNMENT_OPTIONS,
    )


def _git_tag_is_readonly(arguments: list[str]) -> bool:
    normalized = [
        "-n" if argument.startswith("-n") and argument[2:].isdigit() else argument
        for argument in arguments
    ]
    return _git_selector_is_readonly(
        normalized,
        positional_modes=_TAG_LIST_FLAGS | _TAG_VERIFY_FLAGS,
        flags=_TAG_READ_FLAGS | {"-n"},
        required_values=_TAG_REQUIRED_VALUE_OPTIONS,
        query_values=_TAG_QUERY_OPTIONS,
        assignment_options=_TAG_ASSIGNMENT_OPTIONS,
    )


def _git_selector_is_readonly(
    arguments: list[str],
    *,
    positional_modes: frozenset[str],
    flags: frozenset[str],
    required_values: frozenset[str],
    query_values: frozenset[str],
    assignment_options: frozenset[str],
) -> bool:
    positionals_allowed = not arguments
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        option = argument.partition("=")[0]
        if argument == "--":
            positionals_allowed = True
        elif not argument.startswith("-"):
            if not positionals_allowed:
                return False
        elif option in positional_modes:
            positionals_allowed = True
        elif option in flags or _option_is_allowed(argument, assignment_options):
            pass
        elif option in required_values:
            index = _consume_required_value(arguments, index, argument)
            if index < 0:
                return False
        elif option in query_values:
            index += int("=" not in argument and _next_is_value(arguments, index))
        else:
            return False
        index += 1
    return True


def _option_is_allowed(argument: str, options: frozenset[str]) -> bool:
    option, separator, value = argument.partition("=")
    return option in options and (not separator or bool(value))


def _consume_required_value(arguments: list[str], index: int, argument: str) -> int:
    if "=" in argument:
        return index if argument.partition("=")[2] else -1
    return index + 1 if _next_is_value(arguments, index) else -1


def _next_is_value(arguments: list[str], index: int) -> bool:
    return (
        index + 1 < len(arguments)
        and arguments[index + 1] != "--"
        and not arguments[index + 1].startswith("-")
    )


def _stash_operation(arguments: list[str]) -> str:
    return arguments[0] if arguments and arguments[0] in {"list", "show"} else "push"


def _git_invocation(tokens: list[str]) -> tuple[str, list[str]] | None:
    if not tokens or _command_name(tokens[0]) != "git":
        return None
    index = 1
    while index < len(tokens):
        argument = tokens[index]
        if argument in _GIT_GLOBAL_VALUE_OPTIONS:
            if index + 1 == len(tokens):
                return None
            index += 2
        elif argument in _GIT_GLOBAL_FLAGS or argument.startswith(
            ("-", "--git-dir=", "--work-tree=", "--namespace=", "--exec-path=")
        ):
            if (
                argument.startswith("-")
                and argument not in _GIT_GLOBAL_FLAGS
                and not argument.startswith(
                    ("--git-dir=", "--work-tree=", "--namespace=", "--exec-path=")
                )
            ):
                return None
            index += 1
        else:
            return argument, tokens[index + 1 :]
    return None


def _shell_tokens(command: str) -> tuple[list[str], str]:
    if any(token in command for token in ("\n", "\r", "$(", "`", "<(", ">(")):
        return [], "shell_syntax_unsupported"
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
    lexer.whitespace_split = True
    lexer.commenters = "#"
    try:
        return list(lexer), ""
    except ValueError:
        return [], "shell_parse_failed"


def _command_name(argument: str) -> str:
    return argument.rsplit("/", maxsplit=1)[-1].lower()
