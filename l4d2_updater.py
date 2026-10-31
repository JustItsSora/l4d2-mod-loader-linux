"""Auto-actualizador del L4D2 Mod Loader.

Descarga la release mas reciente de GitHub y aplica los archivos sobre la
carpeta de la app (instalacion por codigo fuente). No toca el entorno
virtual, ni la configuracion del usuario, ni el juego.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile


REPO_SLUG = "JustItsSora/l4d2-mod-loader-linux"
API_LATEST = "https://api.github.com/repos/%s/releases/latest" % REPO_SLUG
WEB_LATEST = "https://github.com/%s/releases/latest" % REPO_SLUG
USER_AGENT = "l4d2-mod-loader"
TIMEOUT = 20
ASSET_PREFIX = "l4d2-loader-linux"
KEEP_NAMES = (".venv", ".git", "__pycache__", "build", "dist",
              ".pytest_cache", ".backup-previous")
BACKUP_DIR = ".backup-previous"


class UpdateError(Exception):
    """Error legible para mostrar en la interfaz."""


def parse_version(text):
    numbers = re.findall(r"\d+", str(text or ""))
    return tuple(int(number) for number in numbers[:4]) or (0,)


def is_newer(current, latest):
    return parse_version(latest) > parse_version(current)


def app_root():
    return os.path.dirname(os.path.abspath(__file__))


def is_frozen():
    return bool(getattr(sys, "frozen", False))


def format_size(size):
    size = int(size or 0)
    if size <= 0:
        return "?"
    if size < 1024 * 1024:
        return "%d KB" % (size // 1024)
    return "%.1f MB" % (size / (1024.0 * 1024.0))


def _request(url, accept=None, timeout=TIMEOUT):
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    request = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(request, timeout=timeout)


def fetch_latest_release():
    """Release mas reciente publicada en GitHub (dict) o None."""
    try:
        with _request(API_LATEST, "application/vnd.github+json") as response:
            data = json.loads(response.read().decode("utf-8"))
        if isinstance(data, dict) and data.get("tag_name"):
            return data
    except (urllib.error.URLError, OSError, ValueError):
        pass
    try:
        with _request(WEB_LATEST) as response:
            final_url = response.geturl()
    except (urllib.error.URLError, OSError):
        return None
    match = re.search(r"/releases/tag/([^/?#]+)", final_url)
    if not match:
        return None
    return {"tag_name": match.group(1), "assets": [], "body": "",
            "html_url": final_url}


def find_asset(release):
    """Asset zip de la release (preferimos el del port para Linux)."""
    assets = [asset for asset in (release or {}).get("assets") or []
              if str(asset.get("name", "")).lower().endswith(".zip")]
    if not assets:
        return None
    assets.sort(key=lambda asset: (
        0 if str(asset.get("name", "")).startswith(ASSET_PREFIX) else 1,
        str(asset.get("name", ""))))
    return assets[0]


def download_asset(asset, destination, progress=None):
    """Descarga el asset y devuelve la ruta local."""
    url = (asset or {}).get("browser_download_url")
    if not url:
        raise UpdateError("La release no tiene un archivo descargable.")
    total = int((asset or {}).get("size") or 0)
    done = 0
    try:
        with _request(url, timeout=120) as response, \
                open(destination, "wb") as file:
            while True:
                chunk = response.read(262144)
                if not chunk:
                    break
                file.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
    except (urllib.error.URLError, OSError) as error:
        raise UpdateError("No se pudo descargar la actualizacion: %s" % error)
    return destination


def _archive_root(archive):
    with zipfile.ZipFile(archive) as zip_file:
        names = [name for name in zip_file.namelist()
                 if name.strip() and not name.endswith("/")]
    roots = set()
    for name in names:
        parts = name.replace("\\", "/").split("/")
        if len(parts) > 1:
            roots.add(parts[0])
    return sorted(roots)


def _copy_tree(source, target, skip_names=()):
    copied = 0
    for root, dirs, files in os.walk(source):
        dirs[:] = [name for name in dirs if name not in skip_names]
        relative = os.path.relpath(root, source)
        target_root = target if relative == "." else os.path.join(target,
                                                                  relative)
        os.makedirs(target_root, exist_ok=True)
        for name in files:
            if name.endswith(".pyc"):
                continue
            shutil.copy2(os.path.join(root, name),
                         os.path.join(target_root, name))
            copied += 1
    return copied


def backup_current(app_dir, source_dir):
    """Copia los archivos de app_dir que la actualizacion va a pisar."""
    backup_dir = os.path.join(app_dir, BACKUP_DIR)
    try:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [name for name in dirs if name not in KEEP_NAMES]
            relative = os.path.relpath(root, source_dir)
            target_root = (backup_dir if relative == "."
                           else os.path.join(backup_dir, relative))
            for name in files:
                if name.endswith(".pyc"):
                    continue
                origin = (os.path.join(app_dir, relative, name)
                          if relative != "." else os.path.join(app_dir, name))
                if not os.path.isfile(origin):
                    continue
                os.makedirs(target_root, exist_ok=True)
                shutil.copy2(origin, os.path.join(target_root, name))
    except OSError:
        return None
    return backup_dir


def apply_update(archive_path, app_dir):
    """Aplica el zip descargado sobre app_dir. Devuelve un resumen."""
    if not os.path.isfile(archive_path):
        raise UpdateError("No se encontro el archivo descargado.")
    if not os.path.isdir(app_dir):
        raise UpdateError("No se encontro la carpeta de la app.")
    try:
        with zipfile.ZipFile(archive_path) as zip_file:
            bad = zip_file.testzip()
        if bad:
            raise UpdateError("El archivo descargado esta danado.")
    except zipfile.BadZipFile:
        raise UpdateError("El archivo descargado no es un zip valido.")
    with tempfile.TemporaryDirectory() as work:
        try:
            with zipfile.ZipFile(archive_path) as zip_file:
                zip_file.extractall(work)
        except (OSError, zipfile.BadZipFile) as error:
            raise UpdateError("No se pudo descomprimir la actualizacion: %s"
                              % error)
        roots = [name for name in os.listdir(work)
                 if os.path.isdir(os.path.join(work, name))]
        source = os.path.join(work, roots[0]) if len(roots) == 1 else work
        backup = backup_current(app_dir, source)
        try:
            files = _copy_tree(source, app_dir, skip_names=KEEP_NAMES)
        except OSError as error:
            raise UpdateError("No se pudieron copiar los archivos: %s" % error)
    return {"files": files, "backup": backup}


def restart(app_dir):
    """Relanza la app (para una build compilada usa el propio ejecutable)."""
    try:
        if is_frozen():
            command = [sys.executable]
        else:
            command = [sys.executable or "python3",
                       os.path.join(app_dir, "main.py")]
        subprocess.Popen(command, cwd=app_dir, start_new_session=True,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False


def release_notes(release, limit=1200):
    text = str((release or {}).get("body") or "").strip()
    if not text:
        return "La release no trae notas de cambios."
    if len(text) > limit:
        text = text[:limit].rstrip() + "..."
    return text
