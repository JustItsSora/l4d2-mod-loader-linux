#!/usr/bin/env bash
# Lanzador para MX Linux / Debian / Ubuntu. Crea un venv local en la primera ejecución.
set -e
cd "$(dirname "$(readlink -f "$0")")"

if [ ! -d .venv ]; then
  echo "[*] Creando entorno virtual (.venv)..."
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install "flet[desktop]==0.86.5"
fi

# Dependencias del cliente Flet (GTK3, mpv, portapapeles). Instalar si faltan:
missing=""
for pkg in libgtk-3-0 libmpv2 xclip xdg-utils; do
  dpkg -s "$pkg" >/dev/null 2>&1 || missing="$missing $pkg"
done
if [ -n "$missing" ]; then
  echo "[!] Faltan paquetes:$missing"
  echo "    Instala con: sudo apt install$missing"
fi

exec .venv/bin/python main.py "$@"
