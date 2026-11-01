# L4D2 Mod Loader - Versus

> **Port para Linux.** Este repositorio es la adaptacion para Linux del
> proyecto original **L4D2 Mod Loader - Versus** de **Tokyossz**
> (<https://github.com/SOYmenchowey/l4d2-loader-mod-versus>), publicado para
> Windows. Aqui se anaden el lanzador `run-linux.sh` (Debian/Ubuntu/MX, Fedora,
> Arch, openSUSE y distros inmutables como Bazzite), la entrada de menu
> `.desktop`, los hooks de PyInstaller para Linux, la deteccion de Steam
> Flatpak y de bibliotecas en discos montados, y el detector de Workshop en
> `steamapps/workshop/content/550`.
> Ver `NOTICE.md` para el detalle de autoria y licencia.

**Version actual: 1.4.** La version aparece en la interfaz y en el reporte de diagnostico copiado para identificar cada entrega.

Herramienta para gestionar addons de **Left 4 Dead 2** sin mover archivos a mano ni editar `gameinfo.txt` manualmente.

Selecciona tus mods para Versus, activa la configuración y pulsa **JUGAR**.

## Vista previa

| Mods | Quitar addons |
| --- | --- |
| ![Vista de mods](assets/screenshots/mods.png) | ![Modal para quitar addons](assets/screenshots/remove-addons.png) |

| Diagnóstico |
| --- |
| ![Diagnóstico del loader](assets/screenshots/diagnostics.png) |

## Características

* **Explorador de addons del Workshop**: muestra títulos, descripciones e imágenes de preview usando la API pública de Steam con caché local.
* **Activar y quitar mods**: gestiona `gameinfo.txt` mediante `SearchPaths` y crea copias administradas en `mods/<id>/pak01_dir.vpk`.
* **Activación acumulativa**: al habilitar addons sueltos se conservan los que ya estaban activos.
* **Modpacks exclusivos**: al aplicar un preset quedan activos solo los addons de ese modpack; los demás addons del loader se quitan (sin dependencias ni mods extra). Se guarda la configuración anterior en «Última config».
* **Detección de modpacks**: un VPK local que ya incluye varios mods del Workshop se marca como **PACK**; el loader compara el contenido del pack con el de cada addon del Workshop y sabe cuáles trae dentro.
* **Un pack, solo sus mods**: al activar un pack se excluyen de la selección los mods que ya trae dentro y se desactivan (copias del loader y `addonlist.txt`), para que el juego no cargue el mismo contenido dos veces.
* **Categorías automáticas**: Skins, Armas, Sonido, UI, VScripts y Otros.
* **Favoritos y presets (modpacks)**: guarda combinaciones de addons para reutilizarlas rápido.
* **Dependencias sugeridas**: detecta posibles requisitos entre addons y evita ciclos.
* **Ruta manual de L4D2**: permite seleccionar la carpeta del juego o una Steam Library si Steam está en otro disco.
* **Visión de infectado**: permite quitar o restaurar el tinte naranja/azul.
* **Restauración segura**: revierte los cambios hechos por el loader y conserva archivos o ediciones externas.
* **Detección de Workshop**: lee `left4dead2/addons/workshop` y también `steamapps/workshop/content/550`; el watcher detecta cambios sin reiniciar la app.
* **Bloqueo con juego abierto**: evita modificar archivos mientras Left 4 Dead 2 está ejecutándose.
* **Auto-actualizador**: al arrancar consulta las releases de GitHub y avisa en la barra lateral cuando hay una version nueva. El boton «Actualizar» descarga el zip de la release, guarda una copia de los archivos actuales en `.backup-previous`, los reemplaza y pide reiniciar. No toca el entorno virtual (`.venv`), la configuracion del usuario ni el juego.

## Compilar para Linux (opcional)

Cada release trae el ejecutable ya compilado. Para compilarlo tu mismo:

```bash
./build-linux.sh
```

El script crea el entorno virtual, instala `flet[desktop]` y `pyinstaller`, pasa los tests y genera `dist/L4D2 Mod Loader` (un unico archivo). Tambien se puede a mano:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m PyInstaller --noconfirm --clean L4D2_Mod_Loader.spec
```

Notas del build: el cliente de Flet se incrusta en el binario, asi que no hace
falta descargarlo al usar la app. En Linux el cliente vive en
`flet/lib/libapp.so` (no en `data/app.so` como en Windows) y el ejecutable
`flet` debe conservar el permiso de ejecucion dentro del bundle.

## Requisitos

Para usar el `.exe`:

* Windows.
* Left 4 Dead 2 instalado mediante Steam.

Para correr el código fuente:

* Windows.
* Python 3.10 o superior.
* Dependencias de `requirements.txt`.

### Linux (Debian / Ubuntu / MX, Fedora y Bazzite)

```bash
chmod +x run-linux.sh
./run-linux.sh
```

`run-linux.sh` crea un entorno virtual en la primera ejecución, revisa las librerías que necesita Flet (GTK3, mpv, portapapeles, xdg-open) y muestra el comando de instalación según tu distro:

* **Debian / Ubuntu / MX**: `sudo apt install python3-venv libgtk-3-0 libmpv2 xclip wl-clipboard xdg-utils`
* **Fedora**: `sudo dnf install python3 gtk3 mpv-libs wl-clipboard xclip xdg-utils` (`mpv-libs` viene de RPM Fusion Free si no está en tus repos).
* **Bazzite / Silverblue / Kinoite (inmutables)**: prueba `./run-linux.sh` directamente; si faltan librerías, lo más limpio es un contenedor (`distrobox create -n l4d2 -i fedora:latest`, instala los paquetes de Fedora dentro y ejecuta el script ahí) o, si prefieres, `rpm-ostree install mpv-libs wl-clipboard` y reiniciar.

Detalles:

* Detecta Steam en `~/.local/share/Steam`, `~/.steam/steam`, Flatpak (incluido el `data/Steam` del sandbox de Bazzite/Nobara/SteamOS) y Snap, y lee `libraryfolders.vdf` (de `steamapps/` y de `config/`) para otras bibliotecas.
* También busca bibliotecas de Steam en discos montados (`/run/media/<usuario>/...`, `/var/mnt`, `/mnt`, `/media`), típicos de Bazzite y Steam Deck.
* Datos y caché en `~/.local/share/L4D2ModLoader`.
* El estado de «juego abierto» se comprueba leyendo `/proc`.
* Si Steam está en otra ruta, usa **Buscar ruta**.
* Para generar un binario: `pip install -r requirements.txt && pyinstaller --clean --noconfirm L4D2_Mod_Loader.spec`.

## Uso

Si tienes el ejecutable, abre `L4D2 Mod Loader.exe`.

Si Left 4 Dead 2 está instalado dentro de `Program Files`, puede ser necesario ejecutar la app como administrador para permitir cambios en `gameinfo.txt`.

Si la app no detecta tu instalación, usa **Buscar ruta** y selecciona una de estas opciones:

* `...\steamapps\common\Left 4 Dead 2`
* `...\steamapps\common\Left 4 Dead 2\left4dead2`
* una carpeta `SteamLibrary`
* la carpeta `addons` o `workshop` del juego

## Ejecutar desde código fuente

```bash
git clone https://github.com/SOYmenchowey/l4d2-loader-mod-versus.git
cd l4d2-loader-mod-versus
pip install -r requirements.txt
python main.py
```

## Compilar el `.exe`

```bash
pip install -r requirements.txt
pyinstaller --clean --noconfirm "L4D2_Mod_Loader.spec"
```

El ejecutable generado aparecerá en `dist/`.

La compilación incluye el cliente de escritorio de Flet. Puede descargarlo la primera vez al compilar; el `.exe` distribuido no necesita descargar ese cliente al abrirse. Los metadatos e imágenes de Steam sí pueden requerir Internet.

El repositorio no incluye el `.exe` generado. `dist/`, `build/`, `.flet/`, logs, cachés y archivos `.zip` locales están ignorados por Git.

## Glows

Desde la 1.2 el loader ya no crea ni edita glows, para que no pisen los de los modpacks. Si una versión anterior los dejó aplicados (`left4dead2/cfg/l4d2_mod_loader_glows.cfg` y su bloque en `autoexec.cfg`), el loader los retira solo la próxima vez que abre con el juego cerrado. No toca nada de `autoexec.cfg` que no haya escrito él.

## Restauración

**Restaurar original** devuelve `gameinfo.txt`, visión de infectado y copias de mods al estado anterior al loader (y retira cualquier glow heredado de versiones anteriores).

Si otra herramienta o el usuario modificó `gameinfo.txt` después, el loader conserva esos cambios externos y solo retira sus propias entradas administradas.

## Notas

* El programa crea backups automáticos antes de modificar `gameinfo.txt`.
* Los addons de tipo VSCRIPT pueden no funcionar correctamente mediante este método de activación.
* La información del Workshop puede requerir conexión a Internet si no está en caché.
* Cierra Left 4 Dead 2 antes de activar, quitar o restaurar mods.

## Créditos

Proyecto original: **Tokyossz** (<https://github.com/SOYmenchowey/l4d2-loader-mod-versus>).
Port para Linux y adaptaciones: **JustItsSora**.

El repositorio original se publico sin declaracion de licencia, por lo que el
codigo heredado mantiene los derechos de autor de su autor. Las contribuciones
propias de este repositorio (port para Linux, deteccion de packs y gestion de
`addonlist.txt`) se publican bajo MIT; consulta `LICENSE` y `NOTICE.md` para el
detalle.

## Licencia

`LICENSE` (MIT, solo para las contribuciones de este repositorio) y `NOTICE.md`
(autoria y alcance).
