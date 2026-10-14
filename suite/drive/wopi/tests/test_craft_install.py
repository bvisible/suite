# //// Neoffice — added file (no upstream equivalent). The Craft editors' builds are downloaded and unpacked on
# //// the server: what comes in must match its pinned hash, stay inside its folder, and never leave a site
# //// without the editor it had when the new one cannot be installed.
from __future__ import annotations

import hashlib
import io
import os
import stat
import tempfile
import zipfile
from unittest import TestCase
from unittest.mock import patch

from suite.drive.wopi import craft_install as install


def archive(entries: dict, folder: str | None = "app-web-1.0", links: dict | None = None) -> bytes:
    """A zip of ``entries`` (name -> bytes), inside ``folder`` unless it is None."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name, content in entries.items():
            bundle.writestr(f"{folder}/{name}" if folder else name, content)
        for name, target in (links or {}).items():
            info = zipfile.ZipInfo(f"{folder}/{name}" if folder else name)
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            bundle.writestr(info, target)
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, body: bytes, status: int = 200):
        self.body, self.status, self.headers = body, status, {"Content-Length": str(len(body))}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")

    def iter_content(self, size):
        for start in range(0, len(self.body), size):
            yield self.body[start : start + size]


class TestUnpacking(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.root, ignore_errors=True))

    def unpack(self, data: bytes) -> str:
        zip_path = os.path.join(self.root, "build.zip")
        with open(zip_path, "wb") as handle:
            handle.write(data)
        destination = os.path.join(self.root, "out")
        install.unpack(zip_path, destination)
        return destination

    def test_the_top_level_folder_is_dropped(self):
        out = self.unpack(archive({"index.html": b"<html>", "app_bg.wasm": b"\0asm"}))
        self.assertEqual(sorted(os.listdir(out)), ["app_bg.wasm", "index.html"])

    def test_an_archive_without_a_folder_unpacks_as_it_is(self):
        out = self.unpack(archive({"index.html": b"<html>"}, folder=None))
        self.assertEqual(os.listdir(out), ["index.html"])

    def test_a_path_that_climbs_out_of_the_build_is_refused(self):
        for name in ("../escape.txt", "../../etc/passwd", "a/../../escape.txt"):
            with self.assertRaises(ValueError, msg=name):
                self.unpack(archive({name: b"x"}, folder=None))
        self.assertFalse(os.path.exists(os.path.join(self.root, "escape.txt")))

    def test_an_absolute_path_is_refused(self):
        with self.assertRaises(ValueError):
            self.unpack(archive({"/tmp/escape.txt": b"x"}, folder=None))

    def test_a_link_is_refused(self):
        with self.assertRaises(ValueError):
            self.unpack(archive({"index.html": b"<html>"}, links={"loot": "/etc/passwd"}))

    def test_an_archive_that_unpacks_to_too_much_is_refused(self):
        with patch.object(install, "MAX_UNPACKED_BYTES", 10):
            with self.assertRaises(ValueError):
                self.unpack(archive({"index.html": b"x" * 100}))

    def test_an_archive_with_too_many_files_is_refused(self):
        with patch.object(install, "MAX_FILES", 2):
            with self.assertRaises(ValueError):
                self.unpack(archive({"a": b"1", "b": b"2", "c": b"3"}))


class TestInstalling(TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(self.root, ignore_errors=True))
        patcher = patch.object(install, "public_dir", return_value=self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def entry(self, data: bytes, version: str = "1.0", sha256: str | None = None) -> dict:
        return {
            "version": version,
            "url": "https://github.com/bvisible/appcraft/releases/download/v1/app-web.zip",
            "sha256": sha256 or hashlib.sha256(data).hexdigest(),
        }

    def run_install(self, data: bytes, **kwargs):
        with patch.object(install.requests, "get", return_value=FakeResponse(data)):
            install.install("appcraft", self.entry(data, **kwargs))

    def test_a_build_is_installed_with_its_version(self):
        self.run_install(archive({"index.html": b"<html>v1"}), version="1.0")
        self.assertEqual(install.current_version("appcraft"), "1.0")
        with open(os.path.join(self.root, "appcraft", "index.html"), "rb") as handle:
            self.assertEqual(handle.read(), b"<html>v1")
        # Nothing is left behind next to it, but the lock file.
        self.assertEqual(sorted(os.listdir(self.root)), [".install.lock", "appcraft"])

    def test_a_new_version_replaces_the_old_one_whole(self):
        self.run_install(archive({"index.html": b"<html>v1", "old.js": b"1"}), version="1.0")
        self.run_install(archive({"index.html": b"<html>v2"}), version="2.0")
        self.assertEqual(install.current_version("appcraft"), "2.0")
        self.assertEqual(sorted(os.listdir(os.path.join(self.root, "appcraft"))), ["VERSION", "index.html"])

    def test_a_download_that_does_not_match_its_hash_installs_nothing(self):
        data = archive({"index.html": b"<html>"})
        with self.assertRaises(ValueError):
            self.run_install(data, sha256="0" * 64)
        self.assertIsNone(install.current_version("appcraft"))
        self.assertFalse(os.path.exists(os.path.join(self.root, "appcraft")))

    def test_a_failed_update_keeps_the_build_the_site_had(self):
        self.run_install(archive({"index.html": b"<html>v1"}), version="1.0")
        with self.assertRaises(ValueError):
            self.run_install(archive({"index.html": b"<html>v2"}), version="2.0", sha256="f" * 64)
        self.assertEqual(install.current_version("appcraft"), "1.0")

    def test_an_archive_without_a_page_is_not_a_build(self):
        with self.assertRaises(ValueError):
            self.run_install(archive({"readme.txt": b"hi"}))
        self.assertIsNone(install.current_version("appcraft"))

    def test_only_the_releases_of_our_own_forks_are_fetched(self):
        data = archive({"index.html": b"<html>"})
        entry = self.entry(data)
        entry["url"] = "https://example.com/app-web.zip"
        with patch.object(install.requests, "get") as fetch:
            with self.assertRaises(ValueError):
                install.install("appcraft", entry)
        fetch.assert_not_called()

    def test_a_folder_name_cannot_climb(self):
        data = archive({"index.html": b"<html>"})
        with patch.object(install.requests, "get") as fetch:
            for name in ("../outside", ".hidden", "a/b"):
                with self.assertRaises(ValueError, msg=name):
                    install.install(name, self.entry(data))
        fetch.assert_not_called()

    def test_an_oversized_download_is_stopped(self):
        data = archive({"index.html": b"x" * 1000})
        with patch.object(install, "MAX_DOWNLOAD_BYTES", 10):
            with self.assertRaises(ValueError):
                self.run_install(data)


class TestTheMigrateHook(TestCase):
    def test_a_failing_install_never_fails_the_migrate(self):
        with (
            patch.object(install.frappe, "conf", {}, create=True),
            patch.object(install, "ensure_installed", side_effect=RuntimeError("no network")),
            patch.object(install.frappe, "log_error") as log,
        ):
            install.after_migrate()
        log.assert_called_once()

    def test_a_site_can_opt_out(self):
        with (
            patch.object(install.frappe, "conf", {"craft_editors_install": 0}, create=True),
            patch.object(install, "ensure_installed") as ensure,
        ):
            install.after_migrate()
        ensure.assert_not_called()

    def test_what_is_up_to_date_is_not_downloaded_again(self):
        manifest = {
            "appcraft": {"version": "1.0", "url": "https://github.com/bvisible/x", "sha256": "0" * 64}
        }
        with (
            patch.object(install, "load_manifest", return_value=manifest),
            patch.object(install, "current_version", return_value="1.0"),
            patch.object(install, "install") as fetch,
        ):
            self.assertEqual(install.ensure_installed(), {"appcraft": "up to date"})
        fetch.assert_not_called()

    def test_one_editor_failing_does_not_stop_the_next(self):
        manifest = {
            "a": {"version": "1", "url": "https://github.com/bvisible/a", "sha256": "0" * 64},
            "b": {"version": "1", "url": "https://github.com/bvisible/b", "sha256": "0" * 64},
        }

        def fake(folder, entry):
            if folder == "a":
                raise ValueError("boom")

        with (
            patch.object(install, "load_manifest", return_value=manifest),
            patch.object(install, "current_version", return_value=None),
            patch.object(install, "install", side_effect=fake),
            patch.object(install.frappe, "log_error"),
        ):
            result = install.ensure_installed()
        self.assertEqual(result["a"], "failed: boom")
        self.assertEqual(result["b"], "installed 1")
