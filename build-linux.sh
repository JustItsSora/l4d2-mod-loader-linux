#!/usr/bin/env bash
# Compila el L4D2 Mod Loader para Linux en un unico ejecutable.
# Uso: ./build-linux.sh
set -euo pipefail

cd "$(dirname "$0")"

VENV=".venv"
PY="${VENV}/bin/python"

if [ ! -x "${PY}" ]; then
    echo "==> Creando el entorno virtual"
    python3 -m venv "${VENV}"
fi

echo "==> Instalando dependencias"
"${PY}" -m pip install --upgrade pip >/dev/null
"${PY}" -m pip install -r requirements.txt

echo "==> Ejecutando los tests"
"${PY}" -m pytest -q

echo "==> Compilando con PyInstaller"
"${PY}" -m PyInstaller --noconfirm --clean L4D2_Mod_Loader.spec

BIN="dist/L4D2 Mod Loader"
if [ ! -f "${BIN}" ]; then
    echo "ERROR: no se genero ${BIN}" >&2
    exit 1
fi

chmod +x "${BIN}"
echo "==> Listo: $(pwd)/${BIN}"
echo "    Para publicar: tar -czf l4d2-mod-loader-linux.tar.gz -C dist 'L4D2 Mod Loader'"
