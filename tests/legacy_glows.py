"""Reproduce lo que dejaban las versiones anteriores del loader (glows aplicados).

El loader ya no crea glows; estas pruebas solo necesitan ese estado heredado
para comprobar que se retira sin tocar nada ajeno.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import l4d2_glows as glows


def save_state():
    return True


def _with_managed_block(text):
    cleaned = glows._remove_managed_block(text)
    match = glows.re.search(r"\r\n|\r|\n", cleaned)
    newline = match.group() if match else "\n"
    block = "%s\nexec %s\n%s" % (
        glows.AUTOEXEC_BEGIN, os.path.splitext(glows.CFG_NAME)[0], glows.AUTOEXEC_END)
    block = block.replace("\n", newline) + newline
    if cleaned and not cleaned.endswith(("\r", "\n")):
        block = block.replace(glows.AUTOEXEC_BEGIN, glows._AUTOEXEC_BEGIN_WITH_SEPARATOR, 1)
        return cleaned + newline + block
    return cleaned + block


def apply(game, log=print):
    try:
        with glows.installation_lock(game):
            cfg = glows.cfg_path(game)
            autoexec = glows.autoexec_path(game)
            original = glows._read_optional_bytes(autoexec)
            cfg_before = glows._read_optional_bytes(cfg)
            text, encoding, bom = glows._decode_autoexec(original or b"")
            updated = bom + _with_managed_block(text).encode(encoding)
            glows._commit_glow_files([
                (cfg, cfg_before, b"// cfg heredado\n"),
                (autoexec, original, updated),
            ], lambda: save_state(), log)
    except (OSError, ValueError) as ex:
        log("[!] No se pudo preparar el estado heredado: %s" % ex)
        return False
    return True
