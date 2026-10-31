"""Deteccion de modpacks: VPK que ya incluyen mods del Workshop.

Un modpack es un unico VPK (por ejemplo un pack de 1 GB) que reune el
contenido de varios mods del Workshop. Si se activa el pack y tambien sus
mods por separado, el juego monta el mismo contenido dos veces y aparecen
conflictos de materiales o modelos.

Este modulo compara el indice de archivos del pack con el de cada addon del
Workshop para descubrir cuales ya viene dentro. Solo se lee el arbol de cada
VPK (no los datos), por lo que el coste es bajo y se cachea por archivo.
"""

import os

from l4d2_vpk import read_vpk_index

MIN_MEMBERS = 3
MATCH_RATIO = 0.5
MIN_MATCHED_FILES = 2

_index_cache = {}
_result_cache = {}


def clear_cache():
    _index_cache.clear()
    _result_cache.clear()


def _signature(path):
    try:
        info = os.stat(path)
    except OSError:
        return None
    return (info.st_size, info.st_mtime_ns)


def _index(path):
    signature = _signature(path)
    if signature is None:
        return None
    key = (os.path.abspath(path), signature)
    if key in _index_cache:
        return _index_cache[key]
    index = read_vpk_index(path)
    if len(_index_cache) > 256:
        _index_cache.clear()
    _index_cache[key] = index
    return index


def detect_members(pack_path, candidates):
    """Mods del Workshop incluidos en el pack.

    candidates: lista de dicts con 'id' numerico y 'path'.
    Devuelve {id_del_mod: proporcion_de_archivos_coincidentes}.
    """
    pack_signature = _signature(pack_path)
    if pack_signature is None:
        return {}
    usable = []
    for candidate in candidates:
        addon_id = str(candidate.get("id", ""))
        path = candidate.get("path")
        if not addon_id.isdigit() or not path:
            continue
        signature = _signature(path)
        if signature is None:
            continue
        usable.append((addon_id, path, signature))
    if not usable:
        return {}
    usable.sort()
    cache_key = (os.path.abspath(pack_path), pack_signature,
                 tuple((aid, sig) for aid, path, sig in usable))
    if cache_key in _result_cache:
        return _result_cache[cache_key]

    pack_index = _index(pack_path)
    members = {}
    if pack_index:
        for addon_id, path, signature in usable:
            index = _index(path)
            if not index:
                continue
            total = len([key for key in index if key[1] != b"addoninfo"])
            if not total:
                continue
            matched = 0
            for key, length in index.items():
                if key[1] == b"addoninfo":
                    continue
                if pack_index.get(key) == length:
                    matched += 1
            if matched < MIN_MATCHED_FILES:
                continue
            ratio = matched / total
            if ratio >= MATCH_RATIO:
                members[addon_id] = ratio
    if len(_result_cache) > 32:
        _result_cache.clear()
    _result_cache[cache_key] = members
    return members


def is_pack(members):
    """Un VPK con varios mods del Workshop dentro se considera modpack."""
    return len(members) >= MIN_MEMBERS
