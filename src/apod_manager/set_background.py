import os
from pathlib import Path
from typing import Callable
from shutil import which
import subprocess


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


def create_plasma_set_background_script(img_path: Path) -> str:
    return (
        'for (const desktop of desktops()) {'
        'desktop.wallpaperPlugin = "org.kde.image";'
        'desktop.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];'
        f' desktop.writeConfig("Image", "{img_path.as_uri()}");'
        '}'
    )


def create_plasma_set_background_args(qdbus: str, img_path: Path) -> list[str]:
    return (
        f"{qdbus} "
        "org.kde.plasmashell "
        "/PlasmaShell "
        "org.kde.PlasmaShell.evaluateScript "
        f"\'{create_plasma_set_background_script(img_path)}\'"
    )


def set_background_plasma(image: Path) -> None:
    if (qdbus := which("qdbus") or which("qdbus6")) is None:
        raise NotImplementedError("Not implemented for plasma environment wwithout 'qdbus' or 'qdbus6'")
    completed = subprocess.run(create_plasma_set_background_args(qdbus, image), shell=True, text=True)
    completed.check_returncode()


def using_plasma() -> Callable[[Path], None] | None:
    if (session := os.getenv("DESKTOP_SESSION")) is None:
        return None
    if "plasma" not in session:
        return None
    return set_background_plasma


posix_detectors: tuple[Callable[[], Callable[[Path], None] | None]] = (
    using_plasma,
)


def set_background_posix(image: Path) -> None:
    for detector in posix_detectors:
        if setter := detector():
            setter(image)
            return
    raise NotImplementedError("Not implemented for current environment.")


OS_SETTERS: dict[str, Callable[[Path], None]] = {
    'nt': set_background_nt,
    'posix': set_background_posix
}


def set_background(image: Path) -> None:
    if os.name not in OS_SETTERS:
        raise SystemError(f'{set_background} is not supported on OS {os.name}')
    OS_SETTERS[os.name](image)
