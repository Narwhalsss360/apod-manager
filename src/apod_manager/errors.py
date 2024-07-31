class APODManagerError(Exception):
    def __init__(self, *args) -> None:
        super().__init__(*args)


class ConfigurationError(Exception):
    def __init__(self, *args) -> None:
        super().__init__(*args)


class DateFormatError(APODManagerError):
    def __init__(self, *args) -> None:
        super().__init__(*args)
