# //// Neoffice — added file (no upstream equivalent): puts the Craft editors' browser builds where the site serves them.
"""Install the Craft editors' browser builds under ``suite/public/craft/``.

The builds are not in git (about 40 MB of WebAssembly each). ``craft_editors.json`` pins, per editor, the
release asset to download and its SHA-256; ``ensure_installed`` fetches what is missing or out of date,
checks the hash, unpacks it with the same suspicion as any download, and swaps the folder in one rename.

It runs after every migrate and never fails one: an editor that cannot be fetched leaves the site on
the build it had (or on Collabora, which the Drive falls back to), and says so in the error log. A site
that sets ``craft_editors_install`` to 0 in its config is left alone.

By hand: ``bench --site <site> execute suite.drive.wopi.craft_install.ensure_installed``.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import stat
import tempfile
import zipfile
from contextlib import contextmanager

import frappe
import requests

MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "craft_editors.json")

# Where a build may come from: the releases of Neoffice's own forks. The hash is the real check.
ALLOWED_URL_PREFIX = "https://github.com/bvisible/"

MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024
MAX_UNPACKED_BYTES = 400 * 1024 * 1024
MAX_FILES = 200
CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 120
CHUNK_BYTES = 1024 * 1024


def public_dir() -> str:
    return frappe.get_app_path("suite", "public", "craft")


def load_manifest() -> dict:
    with open(MANIFEST, encoding="utf-8") as handle:
        return json.load(handle)


def current_version(folder: str) -> str | None:
    try:
        with open(os.path.join(public_dir(), folder, "VERSION"), encoding="utf-8") as handle:
            return handle.read().strip() or None
    except OSError:
        return None


def ensure_installed(only: str | None = None) -> dict:
    """Bring every editor of the manifest (or just ``only``) to its pinned version. Returns what happened."""
    results = {}
    for folder, entry in load_manifest().items():
        if only and folder != only:
            continue
        if current_version(folder) == entry["version"]:
            results[folder] = "up to date"
            continue
        try:
            install(folder, entry)
            results[folder] = f"installed {entry['version']}"
        except Exception as e:
            frappe.log_error(f"Craft editors: could not install {folder}", str(e))
            results[folder] = f"failed: {e}"
    return results


def after_migrate() -> None:
    """The migrate hook: install what is pinned, and never fail the migrate over it."""
    if str(frappe.conf.get("craft_editors_install", 1)) == "0":
        return
    try:
        ensure_installed()
    except Exception as e:
        frappe.log_error("Craft editors: the install step failed", str(e))


def install(folder: str, entry: dict) -> None:
    """Download, check and put in place one editor. Raises, with a message that says why, when it cannot."""
    url = entry["url"]
    if not url.startswith(ALLOWED_URL_PREFIX):
        raise ValueError(f"the build must come from {ALLOWED_URL_PREFIX}")
    if os.path.basename(folder) != folder or folder.startswith("."):
        raise ValueError(f"{folder!r} is not a folder name")

    root = public_dir()
    os.makedirs(root, exist_ok=True)
    with locked(root):
        # Another process (a second site of the bench) may have done it while this one waited.
        if current_version(folder) == entry["version"]:
            return
        work = tempfile.mkdtemp(prefix=f".{folder}-", dir=root)
        try:
            archive = os.path.join(work, "build.zip")
            download(url, archive, entry["sha256"])
            unpacked = os.path.join(work, "new")
            unpack(archive, unpacked)
            if not os.path.isfile(os.path.join(unpacked, "index.html")):
                raise ValueError("the archive has no index.html")
            with open(os.path.join(unpacked, "VERSION"), "w", encoding="utf-8") as handle:
                handle.write(entry["version"] + "\n")
            swap(os.path.join(root, folder), unpacked, os.path.join(work, "old"))
        finally:
            shutil.rmtree(work, ignore_errors=True)


@contextmanager
def locked(root: str):
    """One install at a time per bench: several sites migrate in parallel and share this folder."""
    with open(os.path.join(root, ".install.lock"), "w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def download(url: str, destination: str, sha256: str) -> None:
    digest = hashlib.sha256()
    size = 0
    with requests.get(url, stream=True, timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS)) as response:
        response.raise_for_status()
        if int(response.headers.get("Content-Length") or 0) > MAX_DOWNLOAD_BYTES:
            raise ValueError("the download is larger than expected")
        with open(destination, "wb") as handle:
            for chunk in response.iter_content(CHUNK_BYTES):
                size += len(chunk)
                if size > MAX_DOWNLOAD_BYTES:
                    raise ValueError("the download is larger than expected")
                digest.update(chunk)
                handle.write(chunk)
    if digest.hexdigest() != sha256.lower():
        raise ValueError("the download does not match its pinned SHA-256")


def unpack(archive: str, destination: str) -> None:
    """Unpack a build archive. Its one top-level folder is dropped; nothing may land outside ``destination``."""
    with zipfile.ZipFile(archive) as bundle:
        members = [m for m in bundle.infolist() if not m.is_dir()]
        if not members or len(members) > MAX_FILES:
            raise ValueError("the archive does not look like a build")
        for member in members:
            # Judged on the name as written, before the top-level folder is dropped: a `..` or a leading
            # slash would otherwise pass for that folder.
            if (
                member.filename.startswith("/")
                or ".." in member.filename.split("/")
                or "\\" in member.filename
            ):
                raise ValueError(f"{member.filename}: outside the build")
        prefix = _common_folder(members)
        os.makedirs(destination)
        root = os.path.realpath(destination)
        total = 0
        for member in members:
            if stat.S_ISLNK(member.external_attr >> 16):
                raise ValueError(f"{member.filename}: links are not accepted")
            relative = member.filename[len(prefix) :]
            target = os.path.realpath(os.path.join(root, relative))
            if not relative or os.path.commonpath([root, target]) != root:
                raise ValueError(f"{member.filename}: outside the build")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with bundle.open(member) as source, open(target, "wb") as handle:
                while chunk := source.read(CHUNK_BYTES):
                    total += len(chunk)
                    if total > MAX_UNPACKED_BYTES:
                        raise ValueError("the archive unpacks to more than expected")
                    handle.write(chunk)


def _common_folder(members: list) -> str:
    """The single top-level folder every member sits in (``name/``), or an empty prefix."""
    firsts = {m.filename.split("/", 1)[0] for m in members if "/" in m.filename}
    if len(firsts) == 1 and all("/" in m.filename for m in members):
        return next(iter(firsts)) + "/"
    return ""


def swap(target: str, new: str, old: str) -> None:
    """Put ``new`` at ``target``, keeping what was there until the move has worked."""
    if os.path.isdir(target):
        os.rename(target, old)
    try:
        os.rename(new, target)
    except OSError:
        if os.path.isdir(old):
            os.rename(old, target)
        raise
