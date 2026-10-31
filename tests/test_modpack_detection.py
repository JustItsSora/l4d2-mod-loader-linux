import os
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import l4d2_addonlist as addonlist
import l4d2_core as core
import l4d2_modpacks as modpacks
import l4d2_vpk as vpk

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


def make_vpk(entries):
    """Crea un VPK v1 minimo. entries: [(extension, dir, name, data)]."""
    offsets = []
    position = 0
    for extension, directory, name, data in entries:
        offsets.append(position)
        position += len(data)
    tree = b""
    extensions = []
    for extension, directory, name, data in entries:
        if extension not in extensions:
            extensions.append(extension)
    for extension in extensions:
        tree += extension.encode("utf-8") + b"\0"
        directories = []
        for ext, directory, name, data in entries:
            if ext == extension and directory not in directories:
                directories.append(directory)
        for directory in directories:
            tree += directory.encode("utf-8") + b"\0"
            for index, (ext, dir_name, name, data) in enumerate(entries):
                if ext != extension or dir_name != directory:
                    continue
                tree += name.encode("utf-8") + b"\0"
                tree += struct.pack("<IHHIIH", 0, 0, 0x7fff,
                                    offsets[index], len(data), 0xffff)
            tree += b"\0"
        tree += b"\0"
    tree += b"\0"
    body = b"".join(data for _, _, _, data in entries)
    return struct.pack("<III", 0x55AA1234, 1, len(tree)) + tree + body


class VpkIndexTests(unittest.TestCase):
    def test_index_lists_paths_and_sizes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "pack.vpk")
            with open(path, "wb") as file:
                file.write(make_vpk([
                    ("txt", " ", "addoninfo", b"addontitle \"Pack\""),
                    ("vtf", "materials", "icon", b"12345"),
                ]))
            index = vpk.read_vpk_index(path)
        self.assertEqual(index[(b"materials", b"icon", b"vtf")], 5)
        self.assertIn((b" ", b"addoninfo", b"txt"), index)

    def test_invalid_vpk_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.vpk")
            with open(path, "wb") as file:
                file.write(b"not a vpk")
            self.assertIsNone(vpk.read_vpk_index(path))


class ModpackDetectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write_vpk(self, name, entries):
        path = os.path.join(self.tmp.name, name)
        with open(path, "wb") as file:
            file.write(make_vpk(entries))
        return path

    def test_pack_containing_three_addons_is_detected(self):
        shared = [("vtf", "materials", "icon", b"aaaa"),
                  ("vtf", "materials", "logo", b"bbbb")]
        paths = []
        for index in range(3):
            paths.append(self.write_vpk(
                "%d.vpk" % index,
                shared + [("txt", " ", "addoninfo", b"x%d" % index)]))
        pack = self.write_vpk("pack.vpk", shared + [
            ("txt", " ", "addoninfo", b"pack")])
        candidates = [{"id": str(1000 + i), "path": p}
                      for i, p in enumerate(paths)]
        members = modpacks.detect_members(pack, candidates)
        self.assertEqual(sorted(members), ["1000", "1001", "1002"])
        self.assertTrue(modpacks.is_pack(members))

    def test_unrelated_addons_are_not_members(self):
        pack = self.write_vpk("pack.vpk", [
            ("vtf", "materials", "icon", b"aaaa")])
        other = self.write_vpk("other.vpk", [
            ("vtf", "materials", "icon", b"zzzz"),
            ("vtf", "materials", "logo", b"yyyy")])
        members = modpacks.detect_members(
            pack, [{"id": "2001", "path": other}])
        self.assertEqual(members, {})
        self.assertFalse(modpacks.is_pack(members))

    def test_detection_is_cached(self):
        pack = self.write_vpk("pack.vpk", [
            ("vtf", "materials", "icon", b"aaaa")])
        other = self.write_vpk("other.vpk", [
            ("vtf", "materials", "icon", b"aaaa")])
        candidates = [{"id": "3001", "path": other}]
        first = modpacks.detect_members(pack, candidates)
        second = modpacks.detect_members(pack, candidates)
        self.assertEqual(first, second)


class AddonListTests(unittest.TestCase):
    ADDONLIST = ('"AddonList"\n{\n'
                 '\t"workshop\\111.vpk"\t\t"1"\n'
                 '\t"workshop\\222.vpk"\t\t"0"\n'
                 '\t"pack_mods.vpk"\t\t"1"\n'
                 '}\n')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.left4dead2 = os.path.join(self.tmp.name, "left4dead2")
        os.makedirs(self.left4dead2)
        self.path = os.path.join(self.left4dead2, "addonlist.txt")
        with open(self.path, "w") as file:
            file.write(self.ADDONLIST)
        self.old_localappdata = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = os.path.join(self.tmp.name, "appdata")
        self.addCleanup(self.restore_env)

    def restore_env(self):
        if self.old_localappdata is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = self.old_localappdata

    def read(self):
        with open(self.path) as file:
            return file.read()

    def test_disable_workshop_turns_entry_off(self):
        changed = addonlist.disable_workshop(self.tmp.name, ["111"])
        self.assertIn("workshop\\111.vpk", changed)
        self.assertIn('"workshop\\111.vpk"\t\t"0"', self.read())

    def test_restore_puts_previous_value_back(self):
        addonlist.disable_workshop(self.tmp.name, ["111", "222"])
        self.assertTrue(addonlist.restore_entries(self.tmp.name))
        text = self.read()
        self.assertIn('"workshop\\111.vpk"\t\t"1"', text)
        self.assertIn('"workshop\\222.vpk"\t\t"0"', text)

    def test_other_entries_are_untouched(self):
        addonlist.disable_workshop(self.tmp.name, ["111"])
        self.assertIn('"pack_mods.vpk"\t\t"1"', self.read())


class ApplyPackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.left4dead2 = os.path.join(self.tmp.name, "left4dead2")
        os.makedirs(os.path.join(self.left4dead2, "addons", "workshop"))
        with open(os.path.join(self.left4dead2, "gameinfo.txt"), "w") as file:
            file.write(GAMEINFO)
        with open(os.path.join(self.left4dead2, "addonlist.txt"), "w") as file:
            file.write('"AddonList"\n{\n\t"workshop\\111.vpk"\t\t"1"\n}\n')
        self.old_localappdata = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = os.path.join(self.tmp.name, "appdata")
        self.addCleanup(self.restore_env)
        patcher = mock.patch.object(core, "l4d2_running", return_value=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.log = lambda message: None

    def restore_env(self):
        if self.old_localappdata is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = self.old_localappdata

    def addon(self, aid):
        path = os.path.join(self.left4dead2, "addons", "workshop", aid + ".vpk")
        with open(path, "wb") as file:
            file.write(make_vpk([("txt", " ", "addoninfo", aid.encode())]))
        return {"id": aid, "path": path, "size": os.path.getsize(path)}

    def test_pack_is_enabled_and_its_mods_are_disabled(self):
        member = self.addon("111")
        pack = {"id": "local_pack", "path": self.addon("999")["path"],
                "size": 10, "title": "Pack"}
        self.assertTrue(core.apply_pack(
            self.tmp.name, pack, ["111"], self.log))
        self.assertEqual(set(core.currently_enabled(self.tmp.name)),
                         {"local_pack"})
        with open(os.path.join(self.left4dead2, "addonlist.txt")) as file:
            self.assertIn('"workshop\\111.vpk"\t\t"0"', file.read())

    def test_managed_member_is_removed_when_pack_is_applied(self):
        member = self.addon("111")
        self.assertTrue(core.enable(self.tmp.name, [member], self.log))
        pack = {"id": "local_pack", "path": self.addon("999")["path"],
                "size": 10}
        self.assertTrue(core.apply_pack(
            self.tmp.name, pack, ["111"], self.log))
        self.assertEqual(set(core.currently_enabled(self.tmp.name)),
                         {"local_pack"})
        self.assertFalse(os.path.isdir(
            os.path.join(self.tmp.name, "mods", "111")))

    def test_invalid_pack_is_rejected(self):
        self.assertFalse(core.apply_pack(self.tmp.name, {}, [], self.log))
        self.assertFalse(core.apply_pack(
            self.tmp.name, {"id": "../x", "path": "x"}, [], self.log))


if __name__ == "__main__":
    unittest.main()
