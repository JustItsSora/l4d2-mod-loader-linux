import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import l4d2_updater as updater


class FakeResponse:
    def __init__(self, payload=b"", url=""):
        self.payload = payload
        self.url = url

    def read(self, size=-1):
        if size is None or size < 0:
            data = self.payload
            self.payload = b""
            return data
        data = self.payload[:size]
        self.payload = self.payload[size:]
        return data

    def geturl(self):
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class VersionTests(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(updater.parse_version("v1.2"), (1, 2))
        self.assertEqual(updater.parse_version("1.10.3"), (1, 10, 3))
        self.assertEqual(updater.parse_version("v1.1-linux"), (1, 1))
        self.assertEqual(updater.parse_version(""), (0,))

    def test_is_newer(self):
        self.assertTrue(updater.is_newer("1.2", "v1.3"))
        self.assertTrue(updater.is_newer("1.2", "1.2.1"))
        self.assertFalse(updater.is_newer("1.2", "v1.2"))
        self.assertFalse(updater.is_newer("1.3", "v1.2"))

    def test_format_size(self):
        self.assertEqual(updater.format_size(0), "?")
        self.assertEqual(updater.format_size(2048), "2 KB")
        self.assertEqual(updater.format_size(3 * 1024 * 1024), "3.0 MB")


class FetchTests(unittest.TestCase):
    RELEASE = {
        "tag_name": "v1.3",
        "body": "notas",
        "html_url": "https://github.com/JustItsSora/l4d2-mod-loader-linux",
        "assets": [
            {"name": "otra.zip", "size": 10,
             "browser_download_url": "https://example/otra.zip"},
            {"name": "l4d2-loader-linux-1.3.zip", "size": 20,
             "browser_download_url": "https://example/linux.zip"},
        ],
    }

    def test_fetch_uses_the_api(self):
        payload = json.dumps(self.RELEASE).encode("utf-8")

        def request(url, accept=None, timeout=None):
            self.assertTrue(url.endswith("/releases/latest"))
            return FakeResponse(payload)

        with mock.patch.object(updater, "_request", side_effect=request):
            release = updater.fetch_latest_release()
        self.assertEqual(release["tag_name"], "v1.3")

    def test_fetch_falls_back_to_the_web(self):
        def request(url, accept=None, timeout=None):
            if "api.github.com" in url:
                raise OSError("sin red")
            return FakeResponse(b"", url="https://github.com/x/releases/tag/v1.4")

        with mock.patch.object(updater, "_request", side_effect=request):
            release = updater.fetch_latest_release()
        self.assertEqual(release["tag_name"], "v1.4")

    def test_fetch_returns_none_without_network(self):
        def request(url, accept=None, timeout=None):
            raise OSError("sin red")

        with mock.patch.object(updater, "_request", side_effect=request):
            self.assertIsNone(updater.fetch_latest_release())

    def test_find_asset_prefers_the_linux_zip(self):
        asset = updater.find_asset(self.RELEASE)
        self.assertEqual(asset["name"], "l4d2-loader-linux-1.3.zip")

    def test_find_asset_without_zip(self):
        self.assertIsNone(updater.find_asset({"assets": []}))

    def test_release_notes(self):
        self.assertEqual(updater.release_notes({"body": "hola"}), "hola")
        self.assertIn("notas", updater.release_notes(self.RELEASE))
        self.assertTrue(updater.release_notes({}))


class DownloadTests(unittest.TestCase):
    def test_download_writes_the_file(self):
        asset = {"name": "a.zip", "size": 5,
                 "browser_download_url": "https://example/a.zip"}

        def request(url, accept=None, timeout=None):
            return FakeResponse(b"hello")

        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "a.zip")
            with mock.patch.object(updater, "_request", side_effect=request):
                updater.download_asset(asset, dest)
            with open(dest, "rb") as file:
                self.assertEqual(file.read(), b"hello")

    def test_download_without_url_fails(self):
        with self.assertRaises(updater.UpdateError):
            updater.download_asset({}, "dest.zip")

    def test_download_reports_network_errors(self):
        asset = {"browser_download_url": "https://example/a.zip"}

        def request(url, accept=None, timeout=None):
            raise OSError("sin red")

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(updater, "_request", side_effect=request):
                with self.assertRaises(updater.UpdateError):
                    updater.download_asset(asset, os.path.join(tmp, "a.zip"))


class ApplyUpdateTests(unittest.TestCase):
    def make_zip(self, path, entries):
        with zipfile.ZipFile(path, "w") as archive:
            for name, content in entries:
                archive.writestr(name, content)

    def test_files_are_copied_and_venv_is_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            app_dir = os.path.join(tmp, "app")
            os.makedirs(os.path.join(app_dir, ".venv", "lib"))
            with open(os.path.join(app_dir, ".venv", "lib", "python"),
                      "w") as file:
                file.write("entorno")
            with open(os.path.join(app_dir, "main.py"), "w") as file:
                file.write("viejo")
            archive = os.path.join(tmp, "update.zip")
            self.make_zip(archive, [
                ("l4d2-loader-mod-versus-main/main.py", "nuevo"),
                ("l4d2-loader-mod-versus-main/l4d2_updater.py", "modulo"),
            ])
            result = updater.apply_update(archive, app_dir)
            with open(os.path.join(app_dir, "main.py")) as file:
                self.assertEqual(file.read(), "nuevo")
            self.assertTrue(os.path.isfile(
                os.path.join(app_dir, "l4d2_updater.py")))
            with open(os.path.join(app_dir, ".venv", "lib", "python")) as file:
                self.assertEqual(file.read(), "entorno")
            self.assertEqual(result["files"], 2)
            self.assertIsNotNone(result["backup"])
            with open(os.path.join(app_dir, updater.BACKUP_DIR,
                                   "main.py")) as file:
                self.assertEqual(file.read(), "viejo")

    def test_invalid_zip_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = os.path.join(tmp, "bad.zip")
            with open(archive, "w") as file:
                file.write("no soy un zip")
            with self.assertRaises(updater.UpdateError):
                updater.apply_update(archive, tmp)

    def test_missing_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(updater.UpdateError):
                updater.apply_update(os.path.join(tmp, "nada.zip"), tmp)

    def test_zip_without_folder_is_applied_directly(self):
        with tempfile.TemporaryDirectory() as tmp:
            app_dir = os.path.join(tmp, "app")
            os.makedirs(app_dir)
            archive = os.path.join(tmp, "flat.zip")
            self.make_zip(archive, [("main.py", "plano")])
            updater.apply_update(archive, app_dir)
            with open(os.path.join(app_dir, "main.py")) as file:
                self.assertEqual(file.read(), "plano")


if __name__ == "__main__":
    unittest.main()
