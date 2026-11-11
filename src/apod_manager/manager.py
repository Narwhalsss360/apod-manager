import json
import os
import re
from collections.abc import Generator
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import requests
from requests import Response, get

from .apod import APOD
from .errors import APODManagerError, ConfigurationError

DEFAULTS_APODS_PATH: Path = Path.home() / "apods"
DEFAULTS_APODS_MEDIA_PATH: Path = DEFAULTS_APODS_PATH / "images"
DEFAULT_CONFIGURATION_PATH: Path = DEFAULTS_APODS_PATH / "apod-manager.cfg.json"
API_KEY: str = "api_key"
APODS_PATH: str = "apods_path"
APODS_MEDIA_PATH: str = "apods_media_path"

__DEFAULT_CONFIGURATION__: dict[str, str | Path] = {
    API_KEY: "",
    APODS_PATH: str(DEFAULTS_APODS_PATH),
    APODS_MEDIA_PATH: str(DEFAULTS_APODS_PATH),
}

__loaded_configuration__: dict[str, str | Path] | None = None


def _required_cfg_value[T](key: str, value_type: type[T]) -> T:
    assert __loaded_configuration__ is not None
    if key not in __loaded_configuration__:
        raise ConfigurationError(f"The key '{key}' must be in the configuration.")

    if not isinstance(value := __loaded_configuration__.get(key, None), value_type):
        raise ConfigurationError(
            f"Value for key '{key}' must be of type {value_type.__name__}."
        )

    return value


def __validate_configuration__() -> None:
    assert __loaded_configuration__ is not None

    api_key = _required_cfg_value(API_KEY, str)
    _required_cfg_value(APODS_PATH, str)
    _required_cfg_value(APODS_MEDIA_PATH, str)

    if api_key.strip() == "":
        raise ConfigurationError("API key must not be blank")

    Path(__loaded_configuration__[APODS_PATH]).mkdir(parents=True, exist_ok=True)
    Path(__loaded_configuration__[APODS_MEDIA_PATH]).mkdir(parents=True, exist_ok=True)


def load_configuration_from(file: Path) -> None:
    if not file.exists():
        raise ConfigurationError(f"Configuration file {file} does not exist")
    with open(file, "r", encoding="utf-8") as config_file:
        global __loaded_configuration__
        __loaded_configuration__ = json.load(config_file)
    __validate_configuration__()


def __ensure_loaded__() -> None:
    if __loaded_configuration__ is None:
        load_configuration_from(DEFAULT_CONFIGURATION_PATH)


def generate_default_configuration() -> Path:
    if not DEFAULT_CONFIGURATION_PATH.parent.exists():
        DEFAULT_CONFIGURATION_PATH.parent.mkdir()
    with open(DEFAULT_CONFIGURATION_PATH, "w", encoding="utf-8") as configuration_file:
        configuration_file.write(json.dumps(__DEFAULT_CONFIGURATION__, indent=4))
    return DEFAULT_CONFIGURATION_PATH


def api_key() -> str:
    __ensure_loaded__()
    assert __loaded_configuration__ is not None
    return _required_cfg_value(API_KEY, str)


def apods_path() -> Path:
    __ensure_loaded__()
    return Path(_required_cfg_value(APODS_PATH, str))


def apods_media_path() -> Path:
    __ensure_loaded__()
    return Path(_required_cfg_value(APODS_MEDIA_PATH, str))


def path_for(apod_or_date: APOD | datetime | str) -> Path:
    if isinstance(apod_or_date, APOD):
        return path_for(apod_or_date.datetime)
    if isinstance(apod_or_date, datetime):
        return path_for(APOD.datetime_to_api_str(apod_or_date))
    return apods_path() / Path(f"{apod_or_date}.json")


def media_path_for(apod: APOD) -> Path:
    return apods_media_path() / f"{apod.date}.{apod.media_extension}"


def persist_apod(apod: APOD) -> APOD:
    path: Path = path_for(apod)
    with open(path, "w", encoding="utf-8") as apod_file:
        apod_file.write(json.dumps(asdict(apod), indent=4))
    return apod


def persist_apods(apods: list[APOD]) -> list[APOD]:
    for apod in apods:
        persist_apod(apod)
    return apods


def read_all(path: str | Path, encoding: str = "utf-8") -> str:
    with open(path, "r", encoding=encoding) as file:
        return file.read()


def load_apod(path_or_date: str | Path | datetime) -> APOD:
    if isinstance(path_or_date, str):
        if re.match(APOD.API_DATE_RE, path_or_date):
            path_or_date = path_for(path_or_date)
        else:
            path_or_date = Path(path_or_date)
    elif isinstance(path_or_date, datetime):
        path_or_date = path_for(path_or_date)

    return APOD.from_dict(json.loads(read_all(path_or_date)))


def stored_apods() -> Generator[APOD, None, None]:
    for apod_file in filter(
        lambda file: re.match(f"{APOD.API_DATE_RE}.json", file),
        os.listdir(apods_path()),
    ):
        yield APOD.from_dict(json.loads(read_all(apods_path() / apod_file)))


def save_media(apod: APOD) -> Path:
    path: Path = media_path_for(apod)
    if not apod.is_image:
        raise APODManagerError(
            f"Invalid media type: {apod.media_type} -> {apod.media_extension} "
        )
    response: Response = get(apod.best_url)
    response.raise_for_status()
    with open(path, "wb") as media_file:
        media_file.write(response.content)
    return path


def get_single(date: datetime | str | None = None) -> APOD:
    date = APOD.date_as_api_str(date or datetime.now().astimezone())
    if (path := path_for(date)).exists():
        return APOD.from_dict(json.loads(read_all(path)))
    return persist_apod(
        APOD.from_dict(requests.get(f"{APOD.API_ENDPOINT}/{date}").json())
    )


def get_range(date_from: datetime | str, date_to: datetime | str) -> list[APOD]:
    date_from = APOD.date_as_api_str(date_from)
    date_to = APOD.date_as_api_str(date_to)
    received = requests.get(
        APOD.API_ENDPOINT, {"date_from": date_from, "date_to": date_to}
    ).json()

    if not isinstance(received, list):
        raise APODManagerError(
            f"Unknown response received, expected a list, received: {received!r}"
        )
    received = cast(list[Any], received)

    if any(not isinstance(x, dict) for x in received):
        raise APODManagerError(
            f"Unknown response received, expected a list of dict, received: {received!r}"
        )
    received = cast(list[dict[Any, Any]], received)

    return persist_apods([APOD.from_dict(data) for data in received])


__all__ = [
    "api_key",
    "apods_media_path",
    "apods_path",
    "generate_default_configuration",
    "get_range",
    "get_single",
    "load_configuration_from",
    "media_path_for",
    "path_for",
    "persist_apod",
    "read_all",
    "save_media",
    "stored_apods",
]
