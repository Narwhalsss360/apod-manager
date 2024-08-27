from dataclasses import fields
from datetime import datetime
from npycli import CLI, Command, EmptyEntriesError
from pathlib import Path
from sys import argv
from typing import Any, Optional

from . import manager
from .apod import APOD
from .set_background import set_background

cli = CLI()


@cli.cmd(name='list', help='List all stored apods')
def list_apods() -> str:
    s: str = ''
    for apod in manager.stored_apods():
        s += f'{apod}\n'
    return s


@cli.cmd(name='details', help='Show details of a specific apod. For today\'s, use `today` as date')
def details(date: str) -> str:
    if date == 'today':
        date = datetime.now().strftime(APOD.DATETIME_FORMATTER)
    path: Path = manager.path_for_date(date)
    if not path.exists():
        return f'APOD for {date} does not exist, fetch using fetch-single {date}'
    apod: APOD = APOD.load_from(path)
    s: str = ''
    for field in fields(apod):
        s += f'{field.name}: {getattr(apod, field.name)}\n'
    return s


@cli.cmd(name='save-media', help='Save media of a specific apod. For today\'s, use `today` as date')
def save_media(date: str) -> str:
    if date == 'today':
        date = datetime.now().strftime(APOD.DATETIME_FORMATTER)
    path: Path = manager.path_for_date(date)
    if not path.exists():
        return f'APOD for {date} does not exist, fetch using fetch-single {date}'
    return f'Saved media for {date} to {manager.save_media(APOD.load_from(path))}'


@cli.cmd(name='set-bg', help='Set background as image of an apod. For today\'s, use `today` as date')
def set_bg(date: str) -> str:
    if date == 'today':
        date = datetime.now().strftime(APOD.DATETIME_FORMATTER)
    apod_path: Path = manager.path_for_date(date)
    if not apod_path.exists():
        return f'APOD for {date} does not exist, fetch using fetch-single {date}'
    media_path: Path = manager.media_path_for(APOD.load_from(apod_path))
    if not media_path.exists():
        return f'Media for {date} does not exist, save using save-media {date}'
    set_background(media_path)
    return f'Using {media_path} as background'


@cli.cmd(name='help', help='Show this help')
def help_cmd(command_name: Optional[str] = None) -> str:
    if command_name is None:
        s: str = ''
        for command in cli.commands:
            s += f'{command} {command.help}\n'
        return s
    else:
        command: Optional[Command] = cli.get_command(command_name)
        if command is None:
            return f'Command {command_name} not found'
        return f'{command} {command.help}\n'


@cli.retvals()
def retvals(command: Command, retval: Any) -> None:
    if isinstance(retval, list):
        for item in retval:
            retvals(command, item)
    else:
        print(retval)


# @cli.errors()
def errors(command: Command, exception: Exception) -> None:
    print(
        f'A {exception.__class__.__name__} error occurred Running {command.name}:\n{exception}')


def main() -> None:
    cli.add_command(Command.create(manager.generate_default_configuration, name='make-configuration',
                                   help='Generate default configuration'))
    cli.add_command(Command.create(manager.fetch_single, names=('fetch-single', 'fetch'),
                                   help='Fetch a single APOD, For today\'s use `today` as date'))
    cli.add_command(Command.create(manager.fetch_range, name='fetch-range', help='Fetch a date range of APODs'))

    cli.add_command(
        Command.create(manager.fetch_random, name='fetch-random', help='Fetch `count` random APODs, max 100'))

    try:
        cli.exec(argv[1:])
    except EmptyEntriesError:
        return
    except Exception as e:
        print(f'An error occurred: {e}')


if __name__ == '__main__':
    main()
