#!/usr/bin/env bash
# Lanzador para Linux: Debian/Ubuntu/MX, Fedora y distros inmutables (Bazzite,
# Silverblue, Kinoite). Crea un venv local en la primera ejecucion.
set -e
cd "$(dirname "$(readlink -f "$0")")"

PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "[!] No se encontro $PYTHON."
  echo "    Debian/Ubuntu: sudo apt install python3 python3-venv"
  echo "    Fedora:        sudo dnf install python3"
  echo "    Bazzite:       usa un contenedor: distrobox create -n l4d2 -i fedora:latest"
  exit 1
fi

if [ ! -d .venv ]; then
  echo "[*] Creando entorno virtual (.venv)..."
  if ! "$PYTHON" -m venv .venv; then
    rm -rf .venv
    echo "[!] No se pudo crear el entorno virtual."
    echo "    Debian/Ubuntu: sudo apt install python3-venv"
    echo "    Fedora/Bazzite: sudo dnf install python3 (o usa distrobox)"
    exit 1
  fi
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install "flet[desktop]==0.86.5"
fi

# --- Dependencias del cliente Flet (GTK3, mpv, portapapeles, xdg-open) -------
# Se comprueban las librerias reales (ldconfig) y no el gestor de paquetes, asi
# funciona igual en apt, dnf y rpm-ostree.
have_lib() {
  local ldconfig
  ldconfig="$(command -v ldconfig || echo /sbin/ldconfig)"
  "$ldconfig" -p 2>/dev/null | grep -q "$1"
}

missing=""
have_lib "libgtk-3.so.0" || missing="$missing gtk3"
have_lib "libmpv.so"     || missing="$missing mpv"
command -v xdg-open >/dev/null 2>&1 || missing="$missing xdg-utils"
if [ -n "$WAYLAND_DISPLAY" ]; then
  command -v wl-copy >/dev/null 2>&1 || command -v xclip >/dev/null 2>&1 || missing="$missing clipboard"
else
  command -v xclip >/dev/null 2>&1 || command -v xsel >/dev/null 2>&1 || missing="$missing clipboard"
fi

if [ -n "$missing" ]; then
  echo "[!] Faltan componentes:$missing"
  . /etc/os-release 2>/dev/null || true
  family="${ID:-} ${ID_LIKE:-}"
  if [ -e /run/ostree-booted ] || command -v rpm-ostree >/dev/null 2>&1; then
    # Bazzite / Silverblue / Kinoite: sistema de solo lectura.
    echo "    Sistema inmutable detectado (${PRETTY_NAME:-Fedora Atomic})."
    if command -v ujust >/dev/null 2>&1; then
      echo "    Opcion 1 (recomendada en Bazzite): ujust game-support"
    fi
    echo "    Opcion 2: ejecutar dentro de un contenedor:"
    echo "      distrobox create -n l4d2 -i fedora:latest"
    echo "      distrobox enter l4d2 -- sudo dnf install -y python3 gtk3 mpv-libs wl-clipboard xdg-utils"
    echo "      distrobox enter l4d2 -- ./run-linux.sh"
    echo "    Opcion 3: sudo rpm-ostree install mpv-libs wl-clipboard  (y reiniciar)"
  elif echo "$family" | grep -qiE "fedora|rhel|centos"; then
    echo "    Instala con: sudo dnf install gtk3 mpv-libs wl-clipboard xclip xdg-utils"
    echo "    (mpv-libs viene de RPM Fusion Free si tu Fedora no lo trae)"
  elif echo "$family" | grep -qiE "arch|manjaro|endeavouros"; then
    echo "    Instala con: sudo pacman -S gtk3 mpv xclip wl-clipboard xdg-utils"
  elif echo "$family" | grep -qiE "suse|opensuse"; then
    echo "    Instala con: sudo zypper install gtk3 mpv xclip wl-clipboard xdg-utils"
  elif echo "$family" | grep -qiE "alpine"; then
    echo "    Instala con: sudo apk add gtk3 mpv xclip wl-clipboard xdg-utils"
  elif echo "$family" | grep -qiE "void"; then
    echo "    Instala con: sudo xbps-install gtk3 mpv xclip wl-clipboard xdg-utils"
  else
    echo "    Instala con: sudo apt install libgtk-3-0 libmpv2 xclip wl-clipboard xdg-utils"
  fi
fi

exec .venv/bin/python main.py "$@"
