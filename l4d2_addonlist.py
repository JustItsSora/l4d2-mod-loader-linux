"""Gestion de left4dead2/addonlist.txt (los addons que L4D2 monta de forma nativa).

El juego usa este archivo para decidir que VPK de left4dead2/addons monta. Un
modpack y los mods del Workshop que ya trae dentro no pueden montarse a la
vez: el juego cargaria dos veces el mismo contenido. Este modulo cambia solo
las entradas indicadas y recuerda el valor anterior para poder restaurarlo.
"""

import hashlib
import json
import os
import re

from l4d2_storage import _atomic_write_text, app_dir

STATE_NAME = "native_addons.json"


def addonlist_path(l4d2):
    return os.path.join(l4d2, "left4dead2", "addonlist.txt")


def _state_path():
    return os.path.join(app_dir(), STATE_NAME)


def _game_key(l4d2):
    return hashlib.sha1(os.path.abspath(l4d2).lower().encode("utf-8")).hexdigest()


def _load_state():
    try:
        with open(_state_path(), encoding="utf-8") as file:
            data = json.load(file)
    except (FileNotFoundError, ValueError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _save_state(data):
    try:
        _atomic_write_text(_state_path(), json.dumps(data, ensure_ascii=False, indent=2))
        return True
    except OSError:
        return False


def read_entries(l4d2):
    """Entradas {nombre: valor} del addonlist.txt actual."""
    path = addonlist_path(l4d2)
    try:
        with open(path, encoding="utf-8", errors="replace") as file:
            text = file.read()
    except OSError:
        return {}
    entries = {}
    for match in re.finditer(r'"([^"\r\n]+)"[ \t]*"([^"\r\n]*)"', text):
        entries[match.group(1)] = match.group(2)
    return entries


def workshop_entry(addon_id):
    return "workshop\\%s.vpk" % addon_id


def set_entry_values(l4d2, values, log=print):
    """Escribe valores exactos en las entradas indicadas.

    values: {nombre_de_entrada: "0" o "1"}. Devuelve {nombre: valor_anterior}
    con las entradas que cambiaron.
    """
    path = addonlist_path(l4d2)
    if not os.path.isfile(path) or not values:
        return {}
    try:
        with open(path, encoding="utf-8", errors="replace") as file:
            text = file.read()
    except OSError as ex:
        log("[!] No se pudo leer addonlist.txt: %s" % ex)
        return {}
    previous = {}
    for name, value in values.items():
        pattern = re.compile(r'("%s"[ \t]*)"([^"\r\n]*)"' % re.escape(name))
        match = pattern.search(text)
        if not match:
            continue
        if match.group(2) == value:
            continue
        previous[name] = match.group(2)
        text = text[:match.start()] + '%s"%s"' % (match.group(1), value) + text[match.end():]
    if not previous:
        return {}
    try:
        _atomic_write_text(path, text)
    except OSError as ex:
        log("[!] No se pudo escribir addonlist.txt: %s" % ex)
        return {}
    return previous


def disable_workshop(l4d2, addon_ids, log=print):
    """Desactiva en addonlist.txt los mods del Workshop indicados."""
    ids = [str(i) for i in addon_ids if str(i).isdigit()]
    if not ids:
        return {}
    values = {workshop_entry(i): "0" for i in ids}
    previous = set_entry_values(l4d2, values, log)
    if previous:
        data = _load_state()
        entry = data.setdefault(_game_key(l4d2), {})
        entry.update(previous)
        if not _save_state(data):
            log("[!] No se pudo guardar el estado de addonlist.txt.")
    return previous


def restore_entries(l4d2, log=print):
    """Devuelve las entradas de addonlist.txt al valor que tenian antes."""
    data = _load_state()
    entry = data.get(_game_key(l4d2))
    if not entry:
        return False
    values = {name: (value if value in ("0", "1") else "1")
              for name, value in entry.items()}
    set_entry_values(l4d2, values, log)
    data.pop(_game_key(l4d2), None)
    if not _save_state(data):
        log("[!] No se pudo actualizar el estado de addonlist.txt.")
    return True


def pending_changes(l4d2):
    """Entradas que el loader dejo desactivadas y todavia no se restauraron."""
    return dict(_load_state().get(_game_key(l4d2), {}))
