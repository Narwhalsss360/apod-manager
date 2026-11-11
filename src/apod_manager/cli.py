from datetime import datetime, timedelta
from pathlib import Path
from re import DOTALL, IGNORECASE, findall
from sys import argv
from typing import Any, cast

import dateutil
import npycli
from npycli import (
    CLI,
    Command,
    CommandParameter,
    EmptyEntriesError,
    ParsingError,
)
from npycli.ansi.const.sgr import (
    BOLD_OR_INCREASED_INTENSITY,
    DEFAULT_RENDITION,
)
from npycli.ansi.sequences import OSC, SGR, ST
from npycli.command import cmd

from . import APOD, manager
from .errors import APODManagerError, ConfigurationError
from .set_background import set_background


def datetime_parser(s: str) -> datetime:
    s = s.strip().lower()
    if s == "today":
        return datetime.now().astimezone()
    if s == "tomorrow":
        return datetime.now().astimezone() + timedelta(days=1)
    if s == "yesterday":
        return datetime.now().astimezone() - timedelta(days=1)

    try:
        return dateutil.parser.parse(s)
    except Exception as error:
        raise ParsingError(s, *error.args) from error


cli = CLI(parsers={datetime: datetime_parser})


@cli.cmd(name="list", help="List all stored apods")
def list_apods() -> str:
    return "\n".join(str(apod) for apod in manager.stored_apods())


def hyperlink(url: str, text: str):
    return f"{OSC}8;;{url}{ST}{text}{OSC}8;;{ST}"


def fmt(prop: str, value: Any) -> str:
    return f"{prop}: {value}"


def fmt_explanation(explanation: str) -> str:
    explanation.replace("<br>", "\n")

    for match, _, url, body in findall(
        r'(<a\b[^>]*?\bhref=(["\'])(.*?)\2[^>]*>(.*?)</a>)',
        explanation,
        flags=IGNORECASE | DOTALL,
    ):
        explanation = explanation.replace(match, hyperlink(url, body))

    for match, body in findall(
        r"(<strong\b[^>]*>(.*?)</strong>)", explanation, IGNORECASE | DOTALL
    ):
        explanation = explanation.replace(
            match, f"{SGR(BOLD_OR_INCREASED_INTENSITY)}{body}{SGR(DEFAULT_RENDITION)}"
        )

    return explanation


@cli.cmd(
    name="details",
    help="Show details of a specific apod. For today's, use `today` as date",
)
def details(date: datetime | None = None, *_, no_ansi: bool = False) -> str:
    date = date or datetime.now().astimezone()
    path: Path = manager.path_for(date)
    if not path.exists():
        return f"APOD for {date} does not exist, fetch using fetch-single {date}"
    apod: APOD = manager.load_apod(date)

    return (
        f"{fmt('Date', apod.date)}\n"
        f"{fmt('Title', apod.title)}\n"
        f"{fmt('Permalink', hyperlink(apod.permalink, apod.permalink))}\n"
        f"{fmt('Media Type', apod.media_type)}\n"
        f"{fmt('HD URL', hyperlink(apod.hdurl, apod.hdurl) if apod.hdurl else None)}\n"
        f"{fmt('Explanation', apod.explanation if no_ansi else fmt_explanation(apod.explanation))}"
    )


@cli.cmd(
    name="save-media",
    help="Save media of a specific apod. For today's, use `today` as date",
)
def save_media(date: datetime | None = None) -> str:
    date = date or datetime.now().astimezone()
    path: Path = manager.path_for(date)
    if not path.exists():
        return f"APOD for {date} does not exist, fetch using fetch-single {date}"
    return f"Saved media for {date} to {manager.save_media(manager.load_apod(date))}"


@cli.cmd(
    name="set-bg",
    help="Set background as image of an apod. For today's, use `today` as date",
)
def set_bg(date: datetime | None = None) -> str:
    date = date or datetime.now().astimezone()
    apod_path: Path = manager.path_for(date)
    if not apod_path.exists():
        return f"APOD for {date} does not exist, fetch using fetch-single {date}"
    media_path: Path = manager.media_path_for(manager.load_apod(date))
    if not media_path.exists():
        return f"Media for {date} does not exist, save using save-media {date}"
    set_background(media_path)
    return f"Using {media_path} as background"


@cli.cmd(
    name="help",
    help=(
        "<...>: Positional or Keyword\n"
        "<*...>: Variable Positional\n"
        "<**...>: Variable Keyword\n"
        "/: Positional / Keyword Only Delimiter\n"
        "<: ...>: Type\n"
        "<: = ...>: Default Value\n"
        "[...]: Boolean Flag (Keyword only, no value needed)\n"
    ),
)
def help_cmd(
    command_name: str | None = None,
    parameter_name: str | None = None,
    /,
    extended: bool = False,
) -> str:
    if extended:
        command_help, parameter_help = (
            npycli.abc.Command.extended_command_help,
            CommandParameter.extended_parameter_help,
        )
    else:
        command_help, parameter_help = (
            npycli.abc.Command.basic_command_help,
            CommandParameter.basic_parameter_help,
        )

    if command_name is None:
        out: str = ""
        for i, command in enumerate(cli.commands):
            out += f"{command_help(command)}"
            if i != len(cli.commands) - 1:
                out += "\n"
        return out

    if (command := cli.get_command(command_name)) is None:
        return f"{command_name} is not a command."

    if parameter_name is not None:
        if (
            parameter := next(
                filter(lambda p: parameter_name in p.names, command.parameters), None
            )
        ) is None:
            return f"'{parameter_name}' is not a parameter"
        return parameter_help(parameter)

    return command_help(command)


@cli.retvals()
def retvals(command: npycli.abc.Command, retval: Any) -> None:
    if isinstance(retval, list):
        for item in cast(list[Any], retval):
            retvals(command, item)
    else:
        print(retval)


def main() -> None:
    cli.add_command(
        Command.create(
            manager.generate_default_configuration,
            name="make-configuration",
            help="Generate default configuration",
        )
    )
    cli.add_command(
        Command.create(
            manager.get_single,
            names=("get-single", "get"),
            help="Fetch/Load a single APOD, For today's use `today` as date",
        )
    )
    cli.add_command(
        Command.create(
            manager.get_range, name="get-range", help="Fetch/Load a date range of APODs"
        )
    )

    try:
        cli.exec(argv[1:])
    except EmptyEntriesError:
        retvals(cmd(help_cmd), help_cmd())
    except KeyboardInterrupt:
        return
    except (APODManagerError, ConfigurationError) as error:
        print(error)


if __name__ == "__main__":
    main()
