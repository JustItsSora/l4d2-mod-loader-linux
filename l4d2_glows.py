"""Limpieza de glows heredados.

El loader ya no crea glows (afectaban a los modpacks). Este modulo solo sabe
detectar y retirar lo que dejaron versiones anteriores: l4d2_mod_loader_glows.cfg
y su bloque gestionado en autoexec.cfg. Nada ajeno al loader se toca.
"""
import codecs
import os
import re
import tempfile

from l4d2_locking import installation_lock
from l4d2_storage import _atomic_write_bytes, app_dir


CFG_NAME = "l4d2_mod_loader_glows.cfg"
STATE_NAME = "glows.json"
AUTOEXEC_BEGIN = "// L4D2 Mod Loader glows BEGIN"
AUTOEXEC_END = "// L4D2 Mod Loader glows END"
_AUTOEXEC_BEGIN_WITH_SEPARATOR = AUTOEXEC_BEGIN + " (separator added)"


def state_path():
    return os.path.join(app_dir(), STATE_NAME)


def cfg_path(l4d2):
    return os.path.join(l4d2, "left4dead2", "cfg", CFG_NAME)


def autoexec_path(l4d2):
    return os.path.join(l4d2, "left4dead2", "cfg", "autoexec.cfg")


def _read_optional_bytes(path):
    try:
        with open(path, "rb") as file:
            return file.read()
    except FileNotFoundError:
        return None


def _decode_autoexec(data):
    for bom, encoding in (
            (codecs.BOM_UTF32_LE, "utf-32-le"),
            (codecs.BOM_UTF32_BE, "utf-32-be"),
            (codecs.BOM_UTF16_LE, "utf-16-le"),
            (codecs.BOM_UTF16_BE, "utf-16-be"),
            (codecs.BOM_UTF8, "utf-8")):
        if data.startswith(bom):
            return data[len(bom):].decode(encoding), encoding, bom
    # ASCII markers can be edited through a one-to-one byte mapping, including
    # ANSI and UTF-8 text. Nothing outside the managed lines is transcoded.
    return data.decode("latin-1"), "latin-1", b""


def _read_text(path):
    return _decode_autoexec(_read_optional_bytes(path) or b"")[0]


def _remove_managed_block(text):
    kept = []
    in_block = False
    separator_index = None
    for match in re.finditer(r"[^\r\n]*(?:\r\n|\r|\n|$)", text):
        line = match.group()
        marker = line.rstrip("\r\n")
        if marker in (AUTOEXEC_BEGIN, _AUTOEXEC_BEGIN_WITH_SEPARATOR):
            if in_block:
                raise ValueError("Bloque de glows anidado en autoexec.cfg")
            separator_index = (len(kept) - 1
                               if marker == _AUTOEXEC_BEGIN_WITH_SEPARATOR and kept else None)
            in_block = True
        elif marker == AUTOEXEC_END:
            if not in_block:
                raise ValueError("Bloque de glows incompleto en autoexec.cfg")
            in_block = False
            # Recover an unterminated original only when no external text follows.
            if separator_index is not None and match.end() == len(text):
                kept[separator_index] = re.sub(r"(?:\r\n|\r|\n)$", "", kept[separator_index])
            separator_index = None
        elif not in_block:
            kept.append(line)
    if in_block:
        raise ValueError("Bloque de glows incompleto en autoexec.cfg")
    return "".join(kept)


def _edit_autoexec(data):
    text, encoding, bom = _decode_autoexec(data)
    return bom + _remove_managed_block(text).encode(encoding)


def _commit_glow_files(changes, save_state, log):
    changes = [(path, before, after) for path, before, after in changes
               if before != after]
    backups = {}
    changed = []
    retained = set()
    try:
        # Prepare every recovery copy before the first game file is changed.
        for path, before, after in changes:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if before is not None:
                fd, backup = tempfile.mkstemp(
                    prefix=os.path.basename(path) + ".recovery-",
                    dir=os.path.dirname(path))
                backups[path] = backup
                with os.fdopen(fd, "wb") as file:
                    file.write(before)
                    file.flush()
                    os.fsync(file.fileno())
        for path, before, after in changes:
            if after is None:
                os.remove(path)
            else:
                _atomic_write_bytes(path, after)
            changed.append(path)
        if not save_state():
            raise OSError("No se pudo guardar la configuracion de glows")
    except Exception:
        for path in reversed(changed):
            try:
                if path in backups:
                    os.replace(backups[path], path)
                else:
                    os.remove(path)
            except OSError as ex:
                if path in backups:
                    retained.add(backups[path])
                    log("[!] Recuperacion pendiente de %s; original en %s: %s"
                        % (path, backups[path], ex))
                else:
                    log("[!] No se pudo retirar el archivo nuevo %s: %s" % (path, ex))
        raise
    finally:
        for backup in backups.values():
            if backup not in retained:
                try:
                    os.remove(backup)
                except FileNotFoundError:
                    pass
                except OSError as ex:
                    log("[!] No se pudo retirar la copia %s: %s" % (backup, ex))
    return bool(changes)


def is_applied(l4d2):
    if not l4d2:
        return False
    with installation_lock(l4d2):
        if _read_optional_bytes(cfg_path(l4d2)) is None:
            return False
        text = _read_text(autoexec_path(l4d2))
        return _remove_managed_block(text) != text


def _forget_state():
    """Borra el registro local de glows de versiones anteriores (si existe)."""
    try:
        os.remove(state_path())
    except FileNotFoundError:
        pass
    except OSError:
        return False
    return True


def restore_glows(l4d2, log=print):
    try:
        with installation_lock(l4d2):
            cfg = cfg_path(l4d2)
            autoexec = autoexec_path(l4d2)
            original = _read_optional_bytes(autoexec)
            cfg_before = _read_optional_bytes(cfg)
            cleaned = (_edit_autoexec(original)
                       if original is not None else None)
            changed = _commit_glow_files([
                (autoexec, original, cleaned),
                (cfg, cfg_before, None),
            ], _forget_state, log)
    except (OSError, ValueError) as ex:
        log("[!] No se pudieron restaurar glows: %s" % ex)
        return False
    if changed:
        log("[OK] Glows del loader restaurados.")
    else:
        log("[*] No había glows del loader para restaurar.")
    return True
