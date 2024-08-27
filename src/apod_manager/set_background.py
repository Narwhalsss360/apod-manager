import os
from pathlib import Path
from typing import Callable


def set_background_nt(image: Path) -> None:
    from ctypes import windll
    from winreg import HKEYType, OpenKeyEx, HKEY_CURRENT_USER, KEY_WRITE, SetValueEx, REG_SZ, CloseKey
    windll.user32.SystemParametersInfoW(20, 0, str(image.absolute()), 0)

    desktop_key: HKEYType = OpenKeyEx(HKEY_CURRENT_USER, 'Control Panel\\Desktop', access=KEY_WRITE)
    try:
        SetValueEx(desktop_key, 'WallPaper', 0, REG_SZ, str(image.absolute()))
    except Exception as e:
        CloseKey(desktop_key)
        raise e
    CloseKey(desktop_key)


OS_SETTERS: dict[str, Callable[[Path], None]] = {
    'nt': set_background_nt
}


def set_background(image: Path) -> None:
    if os.name not in OS_SETTERS:
        raise SystemError(f'{set_background} is not supported on OS {os.name}')
    OS_SETTERS[os.name](image)
