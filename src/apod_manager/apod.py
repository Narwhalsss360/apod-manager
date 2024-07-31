from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from pathlib import Path
import json
import re
from requests import get, Response
from .errors import DateFormatError


@dataclass
class APOD:
    API_ENDPOINT = 'https://api.nasa.gov/planetary/apod'
    DATETIME_FORMATTER = '%Y-%m-%d'
    DATE_FORMAT = 'YYYY-MM-DD'
    DATE_RE = r'\d{4}-\d{2}-\d{2}'

    date: str
    title: str
    explanation: str
    url: str
    media_type: str
    hdurl: Optional[str] = field(default=None)
    concepts: Optional[str] = field(default=None)
    thumbnail_url: Optional[str] = field(default=None)
    copyright: Optional[str] = field(default=None)
    resources: Optional[dict] = field(default=None)
    service_version: Optional[str] = field(default=None)

    @property
    def best_url(self) -> str:
        if self.hdurl is not None:
            return self.hdurl
        return self.url

    @property
    def is_image(self) -> bool:
        return self.media_type == 'image'

    @property
    def datetime(self) -> datetime:
        return datetime(year=int(self.date[0:4]), month=int(self.date[5:7]), day=int(self.date[8:10]))

    @property
    def media_extension(self) -> str:
        ext = self.best_url[self.best_url.rindex('.') + 1:]
        if len(ext) > 4:
            ext = 'jpg'
        return ext

    @staticmethod
    def fetch_single(api_key: str, date: Optional[str | datetime]) -> APOD:
        if date is None:
            date: datetime = datetime.now()
        if isinstance(date, datetime):
            date: str = date.strftime(APOD.DATETIME_FORMATTER)
        if not re.match(APOD.DATE_RE, date):
            raise DateFormatError(f'date must follow format {APOD.DATE_FORMAT}')

        response: Response = get(APOD.API_ENDPOINT, params={
            'api_key': api_key,
            'date': date
        })
        response.raise_for_status()
        return APOD(**response.json())

    @staticmethod
    def load_from(file: Path) -> APOD:
        with open(file, 'r', encoding='utf-8') as apod_file:
            return APOD(**json.loads(apod_file.read()))

    @staticmethod
    def fetch_random(api_key: str, count: int) -> list[APOD]:
        if not (1 <= count <= 100):
            raise ValueError(f'`count` must be between (0, 100]')

        response: Response = get(APOD.API_ENDPOINT, params={
            'api_key': api_key,
            'count': count
        })
        return [APOD(**data) for data in response.json()]

    @staticmethod
    def fetch_range(api_key: str, start_date: datetime | str, end_date: datetime | str) -> list[APOD]:
        if start_date is None:
            start_date: datetime = datetime.now()
        if isinstance(start_date, datetime):
            start_date: str = start_date.strftime(APOD.DATETIME_FORMATTER)
        if not re.match(APOD.DATE_RE, start_date):
            raise DateFormatError(f'start_date must follow format {APOD.DATE_FORMAT}')

        if end_date is None:
            end_date: datetime = datetime.now()
        if isinstance(end_date, datetime):
            end_date: str = end_date.strftime(APOD.DATETIME_FORMATTER)
        if not re.match(APOD.DATE_RE, end_date):
            raise DateFormatError(f'end_date must follow format {APOD.DATE_FORMAT}')

        response: Response = get(APOD.API_ENDPOINT, params={
            'api_key': api_key,
            'start_date': start_date,
            'end_date': end_date
        })
        return [APOD(**data) for data in response.json()]

    def _validate_data(self) -> None:
        if not re.match(APOD.DATE_RE, self.date):
            raise DateFormatError(f'date must follow format {APOD.DATE_FORMAT}')
        if not self.title:
            raise ValueError('APOD must have title')
        if self.url is None and self.hdurl is None:
            raise ValueError('APOD must have at least url or hdurl')

    def __post_init__(self) -> None:
        self._validate_data()

    def __str__(self) -> str:
        return f'{self.date} - {self.media_type} - {self.title}'
