"""Usa el cliente Flet incluido en el binario de Linux, sin descargas."""

import os
import sys
from pathlib import Path


if getattr(sys, 'frozen', False) and sys.platform.startswith('linux'):
    desktop = Path(sys._MEIPASS) / 'flet_desktop' / 'app' / 'flet'
    if not (desktop / 'flet').is_file():
        raise RuntimeError('Falta el cliente Flet incluido en el binario.')
    os.environ['FLET_VIEW_PATH'] = str(desktop)
