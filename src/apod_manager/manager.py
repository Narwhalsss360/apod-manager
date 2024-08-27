import json
import os
import re
from dataclasses import asdict
from pathlib import Path
from requests import get, Response
from typing import Generator
from typing import Optional

from .apod import APOD
from .errors import ConfigurationError, APODManagerError

DEFAULTS_APODS_PATH: Path = Path.home() / Path('Pictures' if os.name == 'nt' else '') / 'apods'
DEFAULTS_APODS_MEDIA_PATH: Path = DEFAULTS_APODS_PATH / 'images'
DEFAULT_CONFIGURATION_PATH: Path = DEFAULTS_APODS_PATH / 'apod-manager.cfg.json'
API_KEY: str = 'api_key'
APODS_PATH: str = 'apods_path'
APODS_MEDIA_PATH: str = 'apods_media_path'

__DEFAULT_CONFIGURATION__: dict[str, str | Path] = {
    API_KEY: '',
    APODS_PATH: str(DEFAULTS_APODS_PATH),
    APODS_MEDIA_PATH: str(DEFAULTS_APODS_PATH)
}

__loaded_configuration__: Optional[dict[str, str | Path]] = None


def __validate_configuration__() -> None:
    if API_KEY not in __loaded_configuration__:
        raise ConfigurationError(f'{API_KEY} is a required key in the configuration file')

    if APODS_PATH not in __loaded_configuration__:
        raise ConfigurationError(f'{APODS_PATH} is a required key in the configuration file')

    if APODS_MEDIA_PATH not in __loaded_configuration__:
        raise ConfigurationError(f'{APODS_MEDIA_PATH} is a required key in the configuration file')

    if __loaded_configuration__[API_KEY].strip() == '':
        raise ConfigurationError(f'API key must not be blank')

    Path(__loaded_configuration__[APODS_PATH]).mkdir(parents=True, exist_ok=True)
    Path(__loaded_configuration__[APODS_MEDIA_PATH]).mkdir(parents=True, exist_ok=True)


def load_configuration_from(file: Path) -> None:
    if not file.exists():
        raise ConfigurationError(f'Configuration file {file} does not exist')
    with open(file, 'r', encoding='utf-8') as config_file:
        global __loaded_configuration__
        __loaded_configuration__ = json.load(config_file)
    __validate_configuration__()


def __ensure_loaded__() -> None:
    if __loaded_configuration__ is None:
        load_configuration_from(DEFAULT_CONFIGURATION_PATH)


def generate_default_configuration() -> Path:
    with open(DEFAULT_CONFIGURATION_PATH, 'w', encoding='utf-8') as configuration_file:
        configuration_file.write(json.dumps(__DEFAULT_CONFIGURATION__, indent=4))
    return DEFAULT_CONFIGURATION_PATH


def api_key() -> str:
    __ensure_loaded__()
    return __loaded_configuration__[API_KEY]


def apods_path() -> Path:
    __ensure_loaded__()
    return Path(__loaded_configuration__[APODS_PATH])


def apods_media_path() -> Path:
    __ensure_loaded__()
    return Path(__loaded_configuration__[APODS_MEDIA_PATH])


def path_for_date(date: str) -> Path:
    return apods_path() / Path(f'{date}.json')


def path_for(apod: APOD) -> Path:
    return path_for_date(apod.date)


def media_path_for(apod: APOD) -> Path:
    return apods_media_path() / f'{apod.date}.{apod.media_extension}'


def store_apod(apod: APOD) -> APOD:
    path: Path = path_for(apod)
    with open(path, 'w', encoding='utf-8') as apod_file:
        apod_file.write(json.dumps(asdict(apod), indent=4))
    return apod


def stored_apods() -> Generator[APOD, None, None]:
    for apod_file in filter(lambda file: re.match(f'{APOD.DATE_RE}.json', file), os.listdir(apods_path())):
        yield APOD.load_from(apods_path() / apod_file)


def save_media(apod: APOD) -> Path:
    path: Path = media_path_for(apod)
    if not apod.is_image:
        raise APODManagerError(f'Invalid media type: {apod.media_type} -> {apod.media_extension} ')
    response: Response = get(apod.best_url)
    response.raise_for_status()
    with open(path, 'wb') as media_file:
        media_file.write(response.content)
    return path


def fetch_single(date: Optional[str] = None) -> APOD:
    if path_for_date(date).exists():
        return APOD.load_from(path_for_date(date))
    return store_apod(APOD.fetch_single(api_key(), date))


def fetch_range(start_date: str, end_date: str) -> list[APOD]:
    apods: list[APOD] = APOD.fetch_range(api_key(), start_date, end_date)
    for apod in apods:
        store_apod(apod)
    return apods


def fetch_random(count: int) -> list[APOD]:
    apods: list[APOD] = APOD.fetch_random(api_key(), count)
    for apod in apods:
        store_apod(apod)
    return apods
