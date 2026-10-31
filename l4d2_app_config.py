import os
import re
import subprocess
import time

from l4d2_platform import IS_WINDOWS, data_base


APP_VERSION = "1.2"
VERSION_LABEL = "Version %s" % APP_VERSION

DEFAULT_WINDOW_WIDTH = 1152
DEFAULT_WINDOW_HEIGHT = 944
MIN_WINDOW_WIDTH = 1040
MIN_WINDOW_HEIGHT = 760
FALLBACK_SCREEN = (1366, 768)


def _run(command):
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.decode("utf-8", "replace")


def _linux_screen_size():
    """Resolucion de la pantalla en Linux (X11 o Wayland con XWayland)."""
    output = _run(["xdpyinfo"])
    match = re.search(r"dimensions:\s+(\d+)x(\d+)", output)
    if match:
        return int(match.group(1)), int(match.group(2))
    output = _run(["xrandr", "--current"])
    sizes = re.findall(r"(\d+)x(\d+)\+\d+\+\d+", output)
    connected = re.findall(r" connected[^\n]*?(\d+)x(\d+)\+\d+\+\d+", output)
    candidates = connected or sizes
    if candidates:
        width, height = candidates[0]
        return int(width), int(height)
    return None


def _linux_work_area():
    """Area de trabajo de la pantalla: (x, y, ancho, alto)."""
    output = _run(["xprop", "-root", "_NET_WORKAREA"])
    match = re.search(r"_NET_WORKAREA(?:\(CARDINAL\))?\s*=\s*"
                      r"(\d+),\s*(\d+),\s*(\d+),\s*(\d+)", output)
    if match:
        x, y, width, height = (int(value) for value in match.groups())
        if width > 0 and height > 0:
            return x, y, width, height
    screen = _linux_screen_size()
    if screen:
        return 0, 0, screen[0], screen[1]
    return 0, 0, FALLBACK_SCREEN[0], FALLBACK_SCREEN[1]


def window_geometry():
    width, height = DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT
    geometry = {}
    try:
        if IS_WINDOWS:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            area = wintypes.RECT()
            if hasattr(user32, "SystemParametersInfoW") and user32.SystemParametersInfoW(
                    0x0030, 0, ctypes.byref(area), 0):
                left, top, right, bottom = area.left, area.top, area.right, area.bottom
            else:
                left, top = 0, 0
                right, bottom = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            dpi = user32.GetDpiForSystem() if hasattr(user32, "GetDpiForSystem") else 96
            scale = (dpi or 96) / 96
            available_w, available_h = (right - left) / scale, (bottom - top) / scale
            if available_w > 0 and available_h > 0:
                width = min(width, max(1, available_w - 32))
                height = min(height, max(1, available_h - 32))
                geometry.update(left=left / scale + (available_w - width) / 2,
                                top=top / scale + (available_h - height) / 2)
                geometry.update(max_width=int(available_w), max_height=int(available_h))
        else:
            screen = _linux_screen_size() or FALLBACK_SCREEN
            work = _linux_work_area() or (0, 0, screen[0], screen[1])
            work_x, work_y, work_w, work_h = work
            width = min(width, max(640, work_w - 24))
            height = min(height, max(480, screen[1] - 120))
            geometry.update(left=max(0, work_x + (work_w - width) // 2), top=0)
            geometry.update(max_width=int(screen[0]), max_height=int(screen[1]))
    except (AttributeError, OSError, ValueError):
        pass
    geometry.update(min_width=min(MIN_WINDOW_WIDTH, width),
                    min_height=min(MIN_WINDOW_HEIGHT, height),
                    width=width, height=height)
    return geometry



def cfg_path(name):
    path = os.path.join(data_base(os.getcwd()), "L4D2ModLoader")
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass
    return os.path.join(path, name)


def dbg(msg):
    try:
        base = data_base(os.getcwd())
        path = os.path.join(base, "L4D2ModLoader")
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "debug.log"), "a",
                  encoding="utf-8") as file:
            file.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), msg))
    except Exception:
        pass


def debug_log(msg):
    print(msg)
    dbg("core: " + str(msg))
