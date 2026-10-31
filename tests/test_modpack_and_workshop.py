import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import l4d2_core as core
import l4d2_diagnostics as diagnostics
import l4d2_game as game

GAMEINFO = """GameInfo
{
    FileSystem
    {
        SearchPaths
        {
            Game            left4dead2
        }
    }
}
"""


def touch(path, data=b"vpk"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as file:
        file.write(data)
    return path


class SteamLibrary(unittest.TestCase):
    """<tmp>/lib/steamapps/common/Left 4 Dead 2 con gameinfo.txt."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.lib = os.path.join(self.tmp.name, "lib")
        self.l4d2 = os.path.join(self.lib, "steamapps", "common", "Left 4 Dead 2")
        self.left4dead2 = os.path.join(self.l4d2, "left4dead2")
        os.makedirs(self.left4dead2)
        with open(os.path.join(self.left4dead2, "gameinfo.txt"), "w") as file:
            file.write(GAMEINFO)
        self.content = os.path.join(self.lib, "steamapps", "workshop", "content", "550")


class WorkshopDetectionTests(SteamLibrary):
    def test_workshop_only_in_steamapps_content_is_detected(self):
        self.assertFalse(game.workshop_detected(self.l4d2))
        touch(os.path.join(self.content, "111", "111.vpk"))
        self.assertTrue(game.workshop_detected(self.l4d2))
        self.assertEqual([a["id"] for a in game.list_addons(self.l4d2)], ["111"])

    def test_addons_workshop_wins_and_no_duplicate_identity(self):
        touch(os.path.join(self.left4dead2, "addons", "workshop", "111.vpk"), b"a")
        touch(os.path.join(self.content, "111", "111.vpk"), b"b")
        touch(os.path.join(self.content, "222", "222.vpk"))
        found = {a["id"]: a for a in game.list_addons(self.l4d2)}
        self.assertEqual(sorted(found), ["111", "222"])
        self.assertIn(os.path.join("addons", "workshop"), found["111"]["path"])
        self.assertEqual(found["222"]["source_kind"], "workshop")

    def test_content_folder_uses_folder_id_even_if_vpk_has_other_name(self):
        touch(os.path.join(self.content, "333", "pak.vpk"))
        self.assertEqual([a["id"] for a in game.list_addons(self.l4d2)], ["333"])

    def test_non_numeric_content_folders_are_ignored(self):
        touch(os.path.join(self.content, "notes", "x.vpk"))
        self.assertEqual(game.list_addons(self.l4d2), [])

    def test_empty_install_reports_no_workshop(self):
        self.assertFalse(game.workshop_detected(self.l4d2))
        self.assertFalse(game.workshop_detected(None))

    def test_diagnostics_use_the_shared_detector(self):
        touch(os.path.join(self.content, "111", "111.vpk"))
        snapshot = diagnostics.collect_health_snapshot(
            {"l4d2": self.l4d2, "addons": [], "selected_ids": set()},
            lambda name: name)
        self.assertTrue(snapshot["workshop_exists"])


class LinuxSteamDiscoveryTests(SteamLibrary):
    def find(self, steam_roots=(), library_roots=()):
        with mock.patch.object(game, "IS_WINDOWS", False), \
                mock.patch.object(game, "_linux_steam_roots", return_value=list(steam_roots)), \
                mock.patch.object(game, "_linux_library_roots", return_value=list(library_roots)):
            return game.find_l4d2(None)

    def test_library_on_mounted_disk_without_vdf_entry(self):
        # Bazzite/Deck: disco en /run/media/... que Steam no lista en el vdf.
        touch(os.path.join(self.lib, "steamapps", "appmanifest_550.acf"), b"x")
        self.assertEqual(self.find(library_roots=[self.lib]), self.l4d2)

    def test_library_listed_only_in_config_libraryfolders(self):
        steam = os.path.join(self.tmp.name, "Steam")
        os.makedirs(os.path.join(steam, "config"))
        with open(os.path.join(steam, "config", "libraryfolders.vdf"), "w") as file:
            file.write('"libraryfolders"\n{\n "1"\n {\n  "path"\t\t"%s"\n }\n}\n' % self.lib)
        touch(os.path.join(self.lib, "steamapps", "appmanifest_550.acf"), b"x")
        self.assertEqual(self.find(steam_roots=[steam]), self.l4d2)

    def test_var_home_and_home_are_not_scanned_twice(self):
        link = os.path.join(self.tmp.name, "link")
        os.symlink(self.lib, link)
        self.assertEqual(len(game._dedupe([self.lib, link])), 1)

    def test_mounted_library_candidates_include_common_layouts(self):
        bases = [os.path.join(self.tmp.name, "disk")]
        os.makedirs(bases[0])
        with mock.patch.object(game, "IS_WINDOWS", False), \
                mock.patch.object(game.glob, "glob",
                                  side_effect=lambda p: bases if p == "/var/mnt/*" else []):
            roots = game._linux_library_roots()
        self.assertIn(os.path.join(bases[0], "SteamLibrary"), roots)
        self.assertIn(bases[0], roots)


class ModpackTests(SteamLibrary):
    def setUp(self):
        super().setUp()
        self.old_localappdata = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = os.path.join(self.tmp.name, "appdata")
        self.addCleanup(self.restore_env)
        patcher = mock.patch.object(core, "l4d2_running", return_value=False)
        self.running = patcher.start()
        self.addCleanup(patcher.stop)
        self.log = lambda message: None

    def restore_env(self):
        if self.old_localappdata is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = self.old_localappdata

    def addon(self, aid):
        path = touch(os.path.join(self.left4dead2, "addons", "workshop", aid + ".vpk"),
                     aid.encode())
        return {"id": aid, "path": path, "size": os.path.getsize(path)}

    def gameinfo_bytes(self):
        with open(os.path.join(self.left4dead2, "gameinfo.txt"), "rb") as file:
            return file.read()

    def active(self):
        return set(core.currently_enabled(self.l4d2))

    def test_modpack_leaves_only_its_addons_active(self):
        a, b, c, d = (self.addon(x) for x in ("1001", "1002", "1003", "1004"))
        self.assertTrue(core.enable(self.l4d2, [a, b, d], self.log))
        self.assertEqual(self.active(), {"1001", "1002", "1004"})

        self.assertTrue(core.apply_modpack(self.l4d2, [b, c], self.log))

        self.assertEqual(self.active(), {"1002", "1003"})
        self.assertFalse(os.path.isdir(os.path.join(self.l4d2, "mods", "1001")))
        self.assertFalse(os.path.isdir(os.path.join(self.l4d2, "mods", "1004")))
        self.assertTrue(os.path.isdir(os.path.join(self.l4d2, "mods", "1003")))

    def test_modpack_does_not_pull_extra_addons(self):
        a, b = self.addon("2001"), self.addon("2002")
        self.assertTrue(core.apply_modpack(self.l4d2, [a], self.log))
        self.assertEqual(self.active(), {"2001"})
        self.assertFalse(os.path.exists(os.path.join(self.l4d2, "mods", b["id"])))

    def test_reapplying_same_modpack_is_a_noop(self):
        a, b = self.addon("3001"), self.addon("3002")
        self.assertTrue(core.apply_modpack(self.l4d2, [a, b], self.log))
        before = self.gameinfo_bytes()
        self.assertTrue(core.apply_modpack(self.l4d2, [a, b], self.log))
        self.assertEqual(self.gameinfo_bytes(), before)

    def test_modpack_keeps_entries_the_loader_does_not_own(self):
        path = os.path.join(self.left4dead2, "gameinfo.txt")
        with open(path, "w") as file:
            file.write(GAMEINFO.replace("Game            left4dead2",
                                        "Game            custom/external\n            Game            left4dead2"))
        a, b = self.addon("4001"), self.addon("4002")
        self.assertTrue(core.enable(self.l4d2, [a], self.log))
        self.assertTrue(core.apply_modpack(self.l4d2, [b], self.log))
        with open(path) as file:
            text = file.read()
        self.assertIn("custom/external", text)
        self.assertEqual(self.active(), {"4002"})

    def test_nothing_changes_while_game_runs(self):
        a, b = self.addon("5001"), self.addon("5002")
        self.assertTrue(core.enable(self.l4d2, [a], self.log))
        self.running.return_value = True
        self.assertFalse(core.apply_modpack(self.l4d2, [b], self.log))
        self.assertEqual(self.active(), {"5001"})

    def test_failed_activation_never_removes_current_addons(self):
        a = self.addon("6001")
        self.assertTrue(core.enable(self.l4d2, [a], self.log))
        missing = {"id": "6002", "path": os.path.join(self.tmp.name, "gone.vpk"), "size": 1}
        self.assertFalse(core.apply_modpack(self.l4d2, [missing], self.log))
        self.assertEqual(self.active(), {"6001"})

    def test_empty_or_invalid_modpack_is_rejected(self):
        self.assertFalse(core.apply_modpack(self.l4d2, [], self.log))
        self.assertFalse(core.apply_modpack(self.l4d2, [{"id": "../x", "path": "p"}], self.log))


if __name__ == "__main__":
    unittest.main()
