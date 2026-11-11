from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, TypeGuard, cast

from apod_manager.errors import DateFormatError


@dataclass(frozen=True, slots=True)
class APOD:
    API_ENDPOINT: ClassVar[str] = "https://science.nasa.gov/wp-json/wp/v2/apod-basic"
    API_DATETIME_FORMATTER: ClassVar[str] = "%y%m%d"
    API_DATE_FORMAT: ClassVar[str] = "YYMMDD"
    API_DATE_RE: ClassVar[str] = r"\d{2}\d{2}\d{2}"

    date: str = field(hash=True)
    post_id: int = field(hash=False)
    title: str = field(hash=False)
    permalink: str = field(hash=False)
    media_type: str = field(hash=False)
    explanation: str = field(hash=False)
    hdurl: str | None = field(default=None)

    @property
    def best_url(self) -> str:
        if self.hdurl is not None:
            return self.hdurl
        return self.permalink

    @property
    def is_image(self) -> bool:
        return self.media_type == "image"

    @property
    def is_video(self) -> bool:
        return self.media_type == "video"

    @property
    def is_other(self) -> bool:
        return self.media_type == "other"

    @property
    def datetime(self) -> datetime:
        return datetime(
            year=int(self.date[0:4]),
            month=int(self.date[5:7]),
            day=int(self.date[8:10]),
        )

    @property
    def media_extension(self) -> str:
        ext = self.best_url[self.best_url.rindex(".") + 1 :]
        if len(ext) > 4:
            ext = "jpg"
        return ext

    @staticmethod
    def datetime_to_api_str(date: datetime) -> str:
        return date.strftime(APOD.API_DATETIME_FORMATTER)

    @staticmethod
    def date_as_api_str(str_or_datetime: datetime | str) -> str:
        if isinstance(str_or_datetime, datetime):
            return APOD.datetime_to_api_str(str_or_datetime)
        str_or_datetime = str_or_datetime.strip()
        if not re.match(APOD.API_DATE_RE, str_or_datetime):
            raise DateFormatError(
                f"The give date string was not of the format {APOD.API_DATE_FORMAT}."
            )
        return str_or_datetime

    @staticmethod
    def from_dict(data: dict[Any, Any] | Any) -> APOD:
        if not isinstance(data, dict):
            raise TypeError("data must be of type dict.")

        data = cast(dict[Any, Any], data)
        date: Any = data.get("date", None)
        post_id: Any = data.get("post_id", None)
        title: Any = data.get("title", None)
        permalink: Any = data.get("permalink", None)
        media_type: Any = data.get("media_type", None)
        explanation: Any = data.get("explanation", None)
        hdurl: Any = data.get("hdurl", None)

        def require[T](value: Any, name: str, value_type: type[T]) -> TypeGuard[T]:
            if isinstance(value, value_type):
                return True
            raise TypeError(
                f"Value {name} must be of type {value_type.__name__}, was {type(value).__name__}."
            )

        def optional[T](
            value: Any, name: str, value_type: type[T]
        ) -> TypeGuard[T | None]:
            if value is None:
                return True

            if isinstance(value, value_type):
                return True
            raise TypeError(
                f"Value {name} must be of type {value_type.__name__}, was {type(value).__name__}."
            )

        assert require(date, "date", str)
        assert require(post_id, "post_id", int)
        assert require(title, "title", str)
        assert require(permalink, "permalink", str)
        assert require(media_type, "media_type", str)
        assert require(explanation, "explanation", str)
        assert optional(hdurl, "hdurl", str)

        return APOD(
            date=date,
            post_id=post_id,
            title=title,
            permalink=permalink,
            media_type=media_type,
            explanation=explanation,
            hdurl=hdurl,
        )

    def __str__(self) -> str:
        return f"{self.date} - {self.media_type} - {self.title}"
