"""Helpers multiplataforma (Windows / Linux) para el loader."""

import os
import shutil
import subprocess
import sys
import tempfile

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")


def data_base(fallback=None):
    """Carpeta base de datos de usuario (LOCALAPPDATA o XDG_DATA_HOME)."""
    local = os.getenv("LOCALAPPDATA")
    if local:
        return local
    if IS_WINDOWS:
        return fallback or tempfile.gettempdir()
    xdg = os.getenv("XDG_DATA_HOME")
    if xdg:
        return xdg
    home = os.path.expanduser("~")
    if home and home != "~":
        return os.path.join(home, ".local", "share")
    return fallback or tempfile.gettempdir()


def addon_separator():
    """Separador usado al escribir 'Game mods<sep>id' en gameinfo.txt."""
    return "\\" if IS_WINDOWS else "/"


def _spawn(cmd):
    subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def open_target(target):
    """Abre una carpeta, URL o URI (steam://) con la app por defecto."""
    if IS_WINDOWS:
        os.startfile(target)  # noqa: S606
        return
    if target.startswith("steam://"):
        steam = shutil.which("steam")
        if steam:
            _spawn([steam, target])
            return
        flatpak = shutil.which("flatpak")
        if flatpak:
            _spawn([flatpak, "run", "com.valvesoftware.Steam", target])
            return
    opener = shutil.which("xdg-open") or shutil.which("gio")
    if not opener:
        raise OSError("No se encontro xdg-open")
    cmd = [opener, target] if opener.endswith("xdg-open") else [opener, "open", target]
    _spawn(cmd)
