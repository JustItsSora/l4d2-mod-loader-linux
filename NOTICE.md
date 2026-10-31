# Avisos de atribucion y licencia

## Proyecto original

**L4D2 Mod Loader - Versus** es obra de **Tokyossz**.

* Repositorio original: https://github.com/SOYmenchowey/l4d2-loader-mod-versus
* El repositorio original fue publicado **sin declaracion de licencia**. Sin
  una licencia explicita, los derechos de autor sobre ese material siguen
  siendo de su autor y no se pueden re-licenciar por terceros.

Todo el codigo heredado de ese proyecto (los modulos `l4d2_*.py`, `main.py`,
`tests/`, `assets/`, el `.spec` de PyInstaller y la estructura general de la
app) mantiene esa situation.

## Port para Linux

Las siguientes contribuciones son obra de **JustItsSora** y se publican bajo la
licencia MIT incluida en `LICENSE`:

* `l4d2_platform.py`: comprobaciones de plataforma, rutas de datos por SO y
  apertura de carpetas/URLs multiplataforma.
* `run-linux.sh`: lanzador para Debian/Ubuntu/MX Linux que crea el `.venv`,
  instala Flet y avisa de paquetes del sistema que faltan.
* `l4d2-mod-loader.desktop`: entrada de menu de aplicaciones para Linux.
* `packaging_hooks/pyi_rth_flet_desktop_linux.py`: hook de PyInstaller para
  el cliente de escritorio de Flet en Linux.
* Adaptaciones en `l4d2_game.py`, `l4d2_storage.py`, `l4d2_workshop.py`,
  `l4d2_clipboard.py`, `l4d2_app_config.py`, `l4d2_core.py`, `main.py` y
  `L4D2_Mod_Loader.spec`: deteccion de Steam en Linux (nativo y Flatpak),
  lectura de `libraryfolders.vdf`, estado del juego mediante `/proc`, datos en
  `XDG_DATA_HOME`, portapapeles con `xclip`/`pbcopy`/`clipboard` y build de
  PyInstaller para Linux.
* Seccion de Linux y notas de instalacion del `README.md`.

## Como puedo usarse este repositorio

Si el autor original anade una licencia a su repositorio (por ejemplo MIT),
esta se aplicara automaticamente a las partes aqui distribuidas. Hasta
entonces, se recomienda citar siempre a **Tokyossz** como autor del proyecto
original y a **JustItsSora** como autor del port para Linux.
