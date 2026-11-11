from typing import Any


class APODManagerError(Exception):
    def __init__(self, *args: Any) -> None:
        super().__init__(*args)


class ConfigurationError(Exception):
    def __init__(self, *args: Any) -> None:
        super().__init__(*args)


class DateFormatError(APODManagerError):
    def __init__(self, *args: Any) -> None:
        super().__init__(*args)


__all__ = ["APODManagerError", "ConfigurationError", "DateFormatError"]
