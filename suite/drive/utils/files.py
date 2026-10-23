# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import os
import shutil
import unicodedata
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from urllib.parse import quote, unquote

import boto3
import frappe
import mimemapper
from botocore.config import Config
from botocore.exceptions import ClientError
from PIL import Image, ImageOps
from werkzeug.http import dump_options_header

from suite.drive.locks.distributed_lock import DistributedLock

from . import STATUS_ACTIVE, get_root_folder

S3_URL_PREFIX = "/api/method/suite.drive.api.s3.fetch?path="
# Sidecar directories under the Drive root, beside the mirrored tree.
TRASH_PREFIX = ".trash"


class FileManager:
    def __init__(self):
        settings = frappe.get_single("Drive Disk Settings")
        self.settings = settings
        self.s3_enabled = settings.enabled
        # not settings.flat: the Single may predate the field, and the doctype
        # overrides __getattribute__ so a missing row raises instead of defaulting
        self.flat = getattr(settings, "flat", 0)
        self.bucket = settings.bucket
        self.site_folder = Path(frappe.get_site_path())

        if self.s3_enabled:
            self.conn = boto3.client(
                "s3",
                aws_access_key_id=settings.aws_key,
                aws_secret_access_key=settings.get_password("aws_secret"),
                endpoint_url=(settings.endpoint_url or None),
                config=Config(signature_version=settings.signature_version),
            )

    def get_prefix(self):
        return self.settings.root_folder or ""

    def get_root_storage_key(self):
        """Return the backend-normalized storage key for the Drive root folder."""
        file_url = get_root_folder()["file_url"]
        if self.s3_enabled:
            file_url = get_s3_key(file_url)
        return storage_key(file_url)

    def _not_if_flat(func):
        """Flat storage has no directories and no per-file paths, so anything that
        rearranges them is a no-op."""

        def wrapper(self, *args, **kwargs):
            if self.flat:
                return
            return func(self, *args, **kwargs)

        return wrapper

    def can_create_thumbnail(self, file):
        # Only images, videos and PDFs get thumbnails.
        if not getattr(file, "mime_type", None):
            return False
        return file.mime_type.startswith(("image", "video")) or file.mime_type == "application/pdf"

    def upload_file(self, current_path: Path, file, create_thumbnail=True) -> None:
        """
        Moves the file from the current path to another path
        """
        if self.s3_enabled:
            self.conn.upload_file(current_path, self.bucket, get_s3_key(file.file_url))
            if create_thumbnail and self.can_create_thumbnail(file):
                frappe.enqueue(
                    self.upload_thumbnail,
                    now=True,
                    at_front=True,
                    file=file,
                    file_path=str(current_path),
                )
            else:
                os.remove(current_path)
        else:
            # //// Neoffice — never over bytes already there (maintenance#1820), as move() refuses: os.rename replaced them
            # //// without a word. The upload endpoint gives a name whose place is free (api/files.py, upload_file).
            destination = self.site_folder / storage_key(file.file_url)
            if destination.exists() or destination.is_symlink():
                frappe.throw(frappe._("A file is already there"), frappe.ValidationError)
            os.rename(current_path, destination)
            if file and create_thumbnail and self.can_create_thumbnail(file):
                frappe.enqueue(
                    self.upload_thumbnail,
                    now=True,
                    at_front=True,
                    file=file,
                    file_path=str(self.site_folder / storage_key(file.file_url)),
                )

    def upload_thumbnail(self, file, file_path: str):
        """
        Creates a thumbnail for the file on disk and then uploads to the thumbnail directory
        """
        save_path = self.get_thumbnail_path(file.name).with_suffix(".png")
        disk_path = str(self.site_folder / save_path)

        try:
            with DistributedLock(file_path, exclusive=False):
                if file.mime_type.startswith("image"):
                    with Image.open(file_path).convert("RGB") as image:
                        image = ImageOps.exif_transpose(image)
                        image.thumbnail((512, 512))
                        image.save(disk_path, format="webp")
                elif file.mime_type.startswith("video"):
                    import av

                    with av.open(file_path) as container:
                        stream = container.streams.video[0]
                        if stream.duration:
                            container.seek(stream.duration // 2, stream=stream)
                        image = next(container.decode(stream)).to_image()
                        image.thumbnail((512, 512))
                        image.save(disk_path, format="webp")
                else:
                    import pymupdf

                    with pymupdf.open(file_path) as pdf:
                        page = pdf.load_page(0)
                        zoom = 512 / max(page.rect.width, page.rect.height)
                        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
                        Image.frombytes("RGB", (pix.width, pix.height), pix.samples).save(
                            disk_path, format="webp"
                        )

                disk_path = Path(disk_path)
                if self.s3_enabled:
                    # Removes original file
                    os.remove(file_path)
                    self.conn.upload_file(disk_path, self.bucket, str(save_path.with_suffix(".thumbnail")))
                    disk_path.unlink()
                else:
                    final_path = disk_path.with_suffix(".thumbnail")
                    disk_path.rename(final_path)
        except BaseException as e:
            frappe.log_error("Thumbnail failed", e)
            if self.s3_enabled:
                try:
                    os.remove(file_path)
                except FileNotFoundError:
                    pass

    def get_disk_path(self, entity, embed=False):
        """
        Helper function to get path of a file
        """
        if self.flat:
            # One namespace under the root, keyed by id — no tree, no team, so a
            # rename or move never touches storage.
            root = Path(self.get_root_storage_key())
            return root / ("embeds" if embed else "") / entity.name

        # perf: stupidly complicated because we use this both with a real entity and a dict
        parent = (
            Path(storage_key(frappe.get_value("File", entity.folder, "file_url") or ""))
            if not hasattr(entity, "parent_path")
            else Path(entity.parent_path)
        )
        name = escape_component(entity.file_name)
        if embed:
            return parent / ".embeds" / name
        return parent / name

    @_not_if_flat
    def create_folder(self, entity):
        """
        Function to create a folder in the S3 bucket or on disk.
        """
        path = self.get_disk_path(entity)
        if self.s3_enabled:
            self.conn.put_object(Bucket=self.bucket, Key=str(path) + "/", Body="")
        else:
            (self.site_folder / path).mkdir(exist_ok=True)
        return str(path) + "/"

    def get_file(self, entity, range_header=None, log=True):
        """
        Function to get a file, with an optional range header for S3 objects
        """
        file_url = storage_key(entity.file_url)
        try:
            if self.s3_enabled and not stored_on_disk(entity.file_url):
                if range_header:
                    buf = self.conn.get_object(Bucket=self.bucket, Key=file_url, Range=range_header)["Body"]
                else:
                    buf = self.conn.get_object(Bucket=self.bucket, Key=file_url)["Body"]
            else:
                with open(self.get_local_path(file_url), "rb") as fh:
                    buf = BytesIO(fh.read())
        except (ClientError, FileNotFoundError, OSError) as e:
            if log:
                frappe.log_error("Drive: could not read file", e)
            frappe.throw("Could not find this file.", frappe.DoesNotExistError)

        return buf

    def get_local_path(self, file_url):
        key = storage_key(file_url)
        # //// Neoffice — upstream only resolved URLs and keys that already name their folder
        # //// (`private/files/…`, `public/files/…`). frappe's public URL `/files/x` has no
        # //// `public/` segment, so it resolved to `<site>/files/x`, outside both roots, and was
        # //// rejected: renaming a public framework file (the wiki's webp conversion of an
        # //// uploaded image) failed in File.validate. Map `files/…` to `public/files/…` the
        # //// way frappe does; the root check below still refuses anything outside the roots.
        if key.startswith("files/"):
            key = "public/" + key
        path = (self.site_folder / key).resolve()
        roots = [
            (self.site_folder / "private" / "files").resolve(),
            (self.site_folder / "public" / "files").resolve(),
        ]
        if not any(path.is_relative_to(root) for root in roots):
            frappe.throw("The File URL you've entered is incorrect", frappe.ValidationError)
        return path

    def presigned_url(self, key, download_name, mime_type=None, expires=3600):
        """Short-lived S3 GET URL, range-capable, served straight to the client."""
        bucket = self.bucket
        params = {
            "Bucket": bucket,
            "Key": key,
            "ResponseContentDisposition": content_disposition(download_name),
        }
        if mime_type:
            params["ResponseContentType"] = mime_type
        return self._presign_client(bucket).generate_presigned_url(
            "get_object", Params=params, ExpiresIn=expires
        )

    def _presign_client(self, bucket):
        """generate_presigned_url signs offline, so it never gets the automatic
        region-redirect retry that a real S3 call (get_object, put_object, ...)
        gets for free. Signed against the wrong region, S3 rejects the URL
        outright with PermanentRedirect instead of serving the object. Detect
        the bucket's real region once (get_bucket_location is itself
        region-agnostic) and sign with a client that matches it."""
        if self.settings.endpoint_url:
            # custom/S3-compatible endpoints (e.g. MinIO) don't do AWS's
            # multi-region redirect dance
            return self.conn

        cache_key = f"drive-s3-bucket-region:{bucket}"
        region = frappe.cache().get_value(cache_key)
        if not region:
            try:
                region = self.conn.get_bucket_location(Bucket=bucket).get("LocationConstraint") or "us-east-1"
            except ClientError:
                region = self.conn.meta.region_name or "us-east-1"
            frappe.cache().set_value(cache_key, region, expires_in_sec=24 * 60 * 60)

        if region == self.conn.meta.region_name:
            return self.conn
        return boto3.client(
            "s3",
            aws_access_key_id=self.settings.aws_key,
            aws_secret_access_key=self.settings.get_password("aws_secret"),
            region_name=region,
            config=Config(signature_version=self.settings.signature_version),
        )

    def iter_blocks(self, entity, block_size=4 * 1024 * 1024):
        """Yield a file's bytes lazily so a worker never holds the whole file."""
        if self.s3_enabled and not stored_on_disk(entity.file_url):
            source = self.get_file(entity)
            try:
                while chunk := source.read(block_size):
                    yield chunk
            finally:
                source.close()
        else:
            with open(self.get_local_path(entity.file_url), "rb") as fh:
                while chunk := fh.read(block_size):
                    yield chunk

    def write_file(self, path: str | Path, content: str):
        if self.s3_enabled:
            pass
        else:
            with open(self.site_folder / path, "w") as f:
                f.write(content)

    @contextmanager
    def open_file(self, path):
        """
        Context manager that yields a file-like object.
        - On disk: opens in binary mode, closes automatically.
        - On S3: yields the botocore StreamingBody, closes automatically.
        """
        if self.s3_enabled and not stored_on_disk(path):
            obj = self.conn.get_object(Bucket=self.bucket, Key=path)
            body = obj["Body"]
            try:
                yield body  # StreamingBody is already a file-like object
            finally:
                body.close()
        else:
            f = open(self.get_local_path(path), "rb")
            try:
                yield f
            finally:
                f.close()

    def fetch_new_files(self) -> dict[Path, tuple[str]]:
        """
        Traverse the site folder and return a list of all yet-uncreated files with information
        Returns path, file size, and modified
        Ignores hidden files
        """
        if self.s3_enabled:
            root_folder = Path(self.get_prefix())
            objects = self.conn.list_objects_v2(Bucket=self.bucket).get("Contents", [])
            basic_files = {}

            # Get files...
            for obj in objects:
                obj_path = Path(obj["Key"])

                if (
                    not obj_path.is_relative_to(root_folder)
                    or obj_path == root_folder
                    or any(str(p).startswith(".") for p in obj_path.parts)
                ):
                    continue
                obj_path = obj_path.relative_to(root_folder)
                basic_files[obj_path] = obj

                # Used to "calculate" natural folders, folders created by Drive are already counted
                # Don't count root folder
                parent_path = obj_path.parent
                if obj_path not in basic_files and parent_path != Path("."):
                    basic_files[parent_path] = {
                        "Key": str(parent_path),
                        "Size": 0,
                        "LastModified": obj["LastModified"],
                        "Folder": True,
                    }

            files = {}

            for path, f in basic_files.items():
                # Drive-created folders - registered S3 objects - have trailing slashes.
                is_folder = f.get("Folder") or f["Key"].endswith("/")
                exists = frappe.get_value(
                    "File",
                    {
                        "file_url": f["Key"].rstrip("/") + ("/" if is_folder else ""),
                        "status": STATUS_ACTIVE,
                        "is_folder": int(is_folder),
                    },
                    "name",
                )
                if exists:
                    continue

                mime_type = "folder" if is_folder else mimemapper.get_mime_type(f["Key"], native_first=False)
                # Relative path is key, DB path is f["Key"]
                files[path] = (f["Size"], f["LastModified"].timestamp(), mime_type, f["Key"])
        else:
            root_folder = self.site_folder / "private" / "files" / self.get_prefix()

            # ... and stitch them together with information
            files = {}
            for f in root_folder.glob("**/*"):
                path = f.relative_to(self.site_folder)
                exists = frappe.get_value(
                    "File",
                    {"file_url": str(path), "status": STATUS_ACTIVE},
                    "name",
                )
                if exists or any(p for p in f.parts if p.startswith(".")):
                    continue

                if f.is_dir():
                    mime_type = "folder"
                else:
                    mime_type = mimemapper.get_mime_type(str(f), native_first=False)

                # Twice `path` for compatability with S3 format
                files[path] = (f.stat().st_size, f.stat().st_mtime, mime_type, str(path))

        return files

    def get_thumbnail_path(self, name):
        return Path(self.get_root_storage_key()) / self.settings.thumbnail_prefix / (name + ".thumbnail")

    def get_thumbnail(self, name):
        return self.get_file(frappe._dict({"file_url": str(self.get_thumbnail_path(name))}), log=False)

    def __get_trash_path(self, entity):
        """Keyed by id, not file_name: trash is one flat directory under a single
        root now, and two teams could each trash a `readme.md`."""
        return Path(self.get_root_storage_key()) / TRASH_PREFIX / entity.name

    def get_trash_path(self, entity):
        """Where move_to_trash put (or will put) this entity's blob, relative
        to the storage root."""
        return self.__get_trash_path(entity)

    # //// Neoffice — added (maintenance#1820): in the tree layout a row that leaves the tree (trashed, deleted) gives up
    # //// its place there. Upstream kept its file_url on the folder's path and its name, where its bytes no longer are
    # //// (move_to_trash took them to the trash, a deletion removed them), as « where a restore would put it back ». The
    # //// next file of that name in that folder got the same url, and frappe's check on private files (File.before_save,
    # //// _validate_private_file_access_in_every_spelling) refused it as a row reaching another owner's bytes: a deposit, a sync, a mail
    # //// saved to the Drive under the name of a colleague's trashed or deleted file failed with « You don't have
    # //// permission to access this file ». Such a row now holds the key of its place in the trash, keyed by its id,
    # //// where its bytes are, and a restore gives it back a place in the tree (api/files.py, toggle_entity_status).
    # //// Flat storage keys every row by its id already: nothing changes there.
    def get_trash_url(self, entity) -> str:
        """The file_url of a row out of the tree: the key of its place in the trash (a folder's with its trailing slash,
        the way create_folder writes it)."""
        return str(self.__get_trash_path(entity)) + ("/" if entity.is_folder else "")

    def holds_trash_url(self, entity) -> bool:
        """Whether `entity`'s file_url is the key of its place in the trash (get_trash_url)."""
        return bool(entity.file_url) and Path(storage_key(entity.file_url)) == self.__get_trash_path(entity)

    # //// Neoffice — added (maintenance#1821): FileManager.move looks for the place among the urls on record first
    # //// Neoffice — `exact` added (maintenance#1828): whether these bytes are another row's too (copied, not moved, to
    # //// the trash; kept at a deletion) asks for the place as the disk spells it, not for a variant of its name
    def named_by_another_row(self, key: str | Path, entity: str | None, exact: bool = False) -> bool:
        """Whether a row other than `entity` (or one below it) names the place `key`, or a place under it, in either
        spelling a row is written with ("private/files/…", "/private/files/…", a folder's with its trailing slash)."""
        key = Path(storage_key(key)).as_posix()
        # //// Neoffice — `spellings` was `exact`, a name the parameter takes (maintenance#1828)
        spellings = (key, "/" + key, key + "/", "/" + key + "/")
        prefixes = (key + "/", "/" + key + "/")

        def under(prefix):
            # what lies below it, the LIKE wildcards of a name taken literally
            return prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"

        # three statements, each an index range on file_url: joined by OR, MariaDB read the whole table (EXPLAIN on
        # prodclone.local, 23.10); an unescaped `_` in the LIKE did the same
        rows = frappe.db.sql(
            """SELECT `name`, `file_url`, `owner` FROM `tabFile` WHERE `file_url` IN %(exact)s
            UNION ALL SELECT `name`, `file_url`, `owner` FROM `tabFile` WHERE `file_url` LIKE %(under)s
            UNION ALL SELECT `name`, `file_url`, `owner` FROM `tabFile` WHERE `file_url` LIKE %(under_slash)s""",
            # //// Neoffice — see `spellings` above
            {"exact": spellings, "under": under(prefixes[0]), "under_slash": under(prefixes[1])},
            as_dict=True,
        )
        user = frappe.session.user
        others = set()
        for row in rows:
            if row.name == entity:
                continue
            # The column compares without case or accents (its collation), the disk does not: « Rapport.pdf » and
            # « rapport.pdf » are two places. A variant of the place is still taken when another owner's row names it:
            # frappe's check on private files and its /private/files/ route (find_file_by_url) compared the same way
            # before the fork of frappe compared urls exactly (maintenance#1828), and a site may run a frappe from before.
            # //// Neoffice — `exact` asks about the bytes, not about the name: only the place itself counts (maintenance#1828).
            if (row.file_url in spellings or row.file_url.startswith(prefixes)) or (
                not exact and user != "Administrator" and row.owner != user
            ):
                others.add(row.name)
        if not others or not entity:
            return bool(others)
        # the rows below `entity` are its own, not others (a trashed folder's files from before the patch still name its
        # old place): one walk up from each of the others, in one query
        below = frappe.db.sql(
            """WITH RECURSIVE `up` (`start`, `name`, `folder`, `depth`) AS (
                SELECT `name`, `name`, `folder`, 0 FROM `tabFile` WHERE `name` IN %(others)s
                UNION ALL
                SELECT `up`.`start`, `t`.`name`, `t`.`folder`, `up`.`depth` + 1
                FROM `tabFile` `t` JOIN `up` ON `t`.`name` = `up`.`folder` WHERE `up`.`depth` < %(depth)s
            )
            SELECT DISTINCT `start` FROM `up` WHERE `folder` = %(entity)s""",
            {"others": tuple(others), "entity": entity, "depth": MAX_DEPTH},
            pluck=True,
        )
        # a chain longer than MAX_DEPTH (a loop in the folders) proves nothing: its row stays another's
        return bool(others - set(below))

    # //// Neoffice — added (maintenance#1820)
    def in_trash(self, url) -> bool:
        """Whether a file_url or storage key is in the trash: a row's own place there, or what lies under a trashed
        folder's."""
        trash = Path(storage_key(self.get_root_storage_key())) / TRASH_PREFIX
        return bool(url) and Path(storage_key(url)).is_relative_to(trash)

    def holds_tree_url(self, entity) -> bool:
        """Whether `entity`'s file_url is its place in the tree: its folder's path and its name (get_disk_path). Not
        an adopted framework upload, which keeps the url frappe gave it, nor an embed, nor anything in flat storage."""
        if self.flat or self.s3_enabled or not entity.file_url:
            return False
        return Path(storage_key(entity.file_url)) == Path(self.get_disk_path(entity))

    @_not_if_flat
    def rename(self, entity):
        if not entity.file_url or entity.mime_type == "frappe/slides":
            return
        new_path = self.get_disk_path(entity)
        return self.move(entity, new_path)

    @_not_if_flat
    # //// Neoffice — `copy` added (maintenance#1828): bytes another row names are copied into the trash, not moved
    def move_to_trash(self, entity, copy=False):
        if not entity.file_url or entity.mime_type in ["frappe/slides", "link"]:
            return

        trash_path = self.__get_trash_path(entity)
        try:
            if self.s3_enabled:
                bucket = self.bucket
                self.conn.copy_object(
                    Bucket=bucket,
                    CopySource={"Bucket": bucket, "Key": storage_key(entity.file_url)},
                    Key=str(trash_path),
                )
                if not copy:  # //// Neoffice — see `copy` above
                    self.conn.delete_object(Bucket=bucket, Key=storage_key(entity.file_url))
            else:
                full_trash_path = self.site_folder / trash_path
                cur_path = self.get_local_path(entity.file_url)
                # //// Neoffice — bytes already in the trash with nothing left at the row's url are this row's own,
                # //// moved by an attempt whose transaction was rolled back afterwards (a folder trashed while its
                # //// request timed out): upstream deleted that directory first and found nothing to move, and the
                # //// folder's files were gone. They stay where they are (maintenance#1820).
                if full_trash_path.exists() and not cur_path.exists():
                    return
                if full_trash_path.exists() and full_trash_path.is_dir():
                    shutil.rmtree(full_trash_path)

                full_trash_path.parent.mkdir(exist_ok=True)
                # //// Neoffice — cur_path is read above, before the trash is looked at
                if copy:
                    # //// Neoffice — see `copy` above
                    if cur_path.is_dir():
                        shutil.copytree(cur_path, full_trash_path)
                    else:
                        shutil.copy2(cur_path, full_trash_path)
                elif cur_path.is_dir():
                    shutil.move(cur_path, full_trash_path)
                else:
                    cur_path.rename(full_trash_path)
        except (FileNotFoundError, ClientError):
            frappe.log_error(f"Moved {entity.name} to trash without it being on disk")
            pass

    # //// Neoffice — `destination` added (maintenance#1820), see below
    @_not_if_flat
    def restore(self, entity, destination: str | None = None):
        """
        Restore a file from the trash.
        """
        # //// Neoffice — `destination` added (maintenance#1820): a trashed row's file_url is its place in the trash now
        # //// (get_trash_url), so the caller names the place in the tree it goes back to. Without it, as upstream. The
        # //// row's name goes along: move() checks that no other row names the place.
        self.move(
            frappe._dict(name=entity.name, file_url=self.__get_trash_path(entity)),
            destination or entity.file_url,
        )

    @_not_if_flat
    def move(self, entity, new_path: str | Path):
        """
        Move a file on disk
        """
        # Callers pass new_path as either a bare key or a stored file_url;
        # normalize both ends to the actual backend key.
        src_key = storage_key(entity.file_url)
        dest_key = storage_key(new_path)
        try:
            if self.s3_enabled:
                bucket = self.bucket
                self.conn.copy_object(
                    Bucket=bucket,
                    CopySource={"Bucket": bucket, "Key": src_key},
                    Key=dest_key,
                )
                self.conn.delete_object(Bucket=bucket, Key=src_key)
            else:
                cur_path = self.get_local_path(src_key)
                dest_path = self.get_local_path(dest_key)
                # //// Neoffice — a move never lands on something already there (maintenance#1820): a file was replaced
                # //// (rename() overwrites) and a folder went inside the folder in place (shutil.move), while the rows
                # //// kept the urls of the place: two rows on the same bytes, or bytes of a live row lost. That happened
                # //// whenever the name handed out was taken (get_new_file_name), or the place held bytes that no Active
                # //// row names (a framework file written at a trashed row's url).
                if dest_path != cur_path and (dest_path.exists() or dest_path.is_symlink()):
                    raise FileExistsError(dest_path)
                # //// Neoffice — nor into the trash (maintenance#1820): a place there is a trashed row's own, which no
                # //// move gives (move_to_trash does). Moving into a trashed folder would leave the bytes where no save
                # //// may name them (File._refuse_drive_own_places); a rename in place inside one stays.
                if self.in_trash(dest_key) and Path(dest_key).parent != Path(src_key).parent:
                    raise IsADirectoryError(dest_path)
                # //// Neoffice — nor onto a place another row names (maintenance#1821), even with nothing there yet: the
                # //// bytes move before the row is saved, and frappe's check, refusing that save, rolled back the rows
                # //// only. A colleague whose own row had been pointed at the empty place in advance then read them.
                if dest_path != cur_path and self.named_by_another_row(dest_key, entity.get("name")):
                    raise FileExistsError(dest_path)
                if cur_path.is_dir():
                    shutil.move(cur_path, dest_path)
                else:
                    cur_path.rename(dest_path)
        # //// Neoffice — the two refusals above, said to the person (maintenance#1820, #1821)
        except FileExistsError:
            frappe.throw(frappe._("A file is already there"), frappe.ValidationError)
        except IsADirectoryError:
            frappe.throw(frappe._("This folder is in the trash"), frappe.ValidationError)
        except BaseException:
            frappe.throw("This file doesn't exist on disk.")
        return new_path

    def copy_file(self, source, target):
        """Duplicate a blob (files only — folders go through create_folder).
        S3-to-S3 copies server-side; a local blob under an S3 config (framework
        adoptions) uploads to the target's key."""
        src_key = storage_key(source.file_url)
        dst_key = storage_key(target.file_url)
        if self.s3_enabled:
            if stored_on_disk(source.file_url):
                self.conn.upload_file(str(self.get_local_path(src_key)), self.bucket, dst_key)
            else:
                # managed copy: copy_object caps at 5GB, conn.copy does multipart
                self.conn.copy(
                    {"Bucket": self.bucket, "Key": src_key},
                    self.bucket,
                    dst_key,
                )
        else:
            shutil.copy2(self.get_local_path(src_key), self.get_local_path(dst_key))
        self._copy_thumbnail(source, target)

    def _copy_thumbnail(self, source, target):
        # cheap to carry over, saves a regeneration; best-effort only
        src_thumb = str(self.get_thumbnail_path(source.name))
        dst_thumb = str(self.get_thumbnail_path(target.name))
        try:
            if self.s3_enabled:
                self.conn.copy_object(
                    Bucket=self.bucket,
                    CopySource={"Bucket": self.bucket, "Key": src_thumb},
                    Key=dst_thumb,
                )
            else:
                shutil.copy2(self.site_folder / src_thumb, self.site_folder / dst_thumb)
        except (ClientError, FileNotFoundError, OSError):
            pass

    def delete_file(self, entity):
        thumbnail_path = self.get_thumbnail_path(entity.name)

        if self.s3_enabled:
            bucket = self.bucket
            try:
                self.conn.delete_object(Bucket=bucket, Key=storage_key(entity.file_url))
                if thumbnail_path:
                    self.conn.delete_object(Bucket=bucket, Key=str(thumbnail_path))
            except Exception:
                pass
        else:
            try:
                path = self.get_local_path(entity.file_url)
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                if thumbnail_path:
                    (self.site_folder / thumbnail_path).unlink()
            except FileNotFoundError:
                pass

    def delete_from_trash(self, entity):
        trash_path = self.__get_trash_path(entity)
        if self.s3_enabled:
            self.conn.delete_object(Bucket=self.bucket, Key=str(trash_path))
            return
        local_path = self.site_folder / trash_path
        if local_path.is_dir():
            shutil.rmtree(local_path)
        else:
            local_path.unlink(missing_ok=True)


# //// Neoffice — added (maintenance#1820): the files of a folder that changed its place on the disk follow its url,
# //// without moving any byte (the folder's directory carried them) and without the save of each: no Version row, no
# //// hook, where saving each one of a large folder's files outlasted the request, whose rollback then left the directory
# //// moved and the rows on their old urls. Each url only changes its prefix, `old` for `new`: no url is made up here.
# //// Only the rows whose url is under their folder's old one (an adopted framework upload or a link keeps its own, and
# //// what lies below it is not looked at); a row out of the tree is left alone with all below it, since its bytes are in
# //// its own place in the trash. One query reads the rows below, one UPDATE per batch writes them.
REPOINT_BATCH = 500
# //// Neoffice — how deep the walks through the folders go (repoint_descendants, FileManager.named_by_another_row): far
# //// beyond any real tree, and under MariaDB's own stop for a recursive query (max_recursive_iterations, 1000 since
# //// 10.6, which ends it without an error); reached, the folders loop (a corrupt `folder`). A walk down that reaches it
# //// changes nothing and says so; a walk up that reaches it leaves the row counted as another's.
MAX_DEPTH = 256


def repoint_descendants(folder: str, old: str | Path, new: str | Path) -> int:
    """Moves the urls of the Active rows below `folder` from under `old` to under `new` (storage keys); returns how many
    changed."""
    rows = frappe.db.sql(
        """WITH RECURSIVE `below` (`name`, `folder`, `file_url`, `depth`) AS (
            SELECT `name`, `folder`, `file_url`, 0 FROM `tabFile` WHERE `folder` = %(folder)s AND `status` = %(active)s
            UNION ALL
            SELECT `t`.`name`, `t`.`folder`, `t`.`file_url`, `below`.`depth` + 1
            FROM `tabFile` `t` JOIN `below` ON `t`.`folder` = `below`.`name`
            WHERE `t`.`status` = %(active)s AND `below`.`depth` < %(depth)s
        )
        SELECT `name`, `folder`, `file_url`, `depth` FROM `below`""",
        {"folder": folder, "active": STATUS_ACTIVE, "depth": MAX_DEPTH},
        as_dict=True,
    )
    if any(row.depth >= MAX_DEPTH for row in rows):
        frappe.throw(frappe._("The folders below this one loop into each other"), frappe.ValidationError)
    children: dict[str, list] = {}
    for row in rows:
        children.setdefault(row.folder, []).append(row)

    urls: dict[str, str] = {}
    walk = [(folder, Path(storage_key(old)), Path(storage_key(new)))]
    while walk:
        parent, parent_old, parent_new = walk.pop()
        for child in children.get(parent, ()):
            if not child.file_url or child.name in urls:
                continue
            key = Path(storage_key(child.file_url))
            if not key.is_relative_to(parent_old):
                continue
            new_key = parent_new / key.relative_to(parent_old)
            urls[child.name] = (
                ("/" if child.file_url.startswith("/") else "")
                + new_key.as_posix()
                + ("/" if child.file_url.endswith("/") else "")
            )
            walk.append((child.name, key, new_key))

    changes = list(urls.items())
    for start in range(0, len(changes), REPOINT_BATCH):
        batch = changes[start : start + REPOINT_BATCH]
        values = [value for change in batch for value in change]
        frappe.db.sql(
            "UPDATE `tabFile` SET `file_url` = CASE `name` "
            + " ".join(["WHEN %s THEN %s"] * len(batch))
            + " END WHERE `name` IN %s",
            [*values, tuple(name for name, _url in batch)],
        )
        # as frappe.db.set_value does
        for name, _url in batch:
            frappe.clear_document_cache("File", name)
    frappe.db.value_cache.pop("File", None)
    return len(changes)


# Utils
def escape_component(file_name):
    """A name is one path component, but `/` is legal in a name and would forge a
    directory level. Escape it rather than renaming the user's file — `%` first, or
    a name containing a literal `%2F` would decode back into a separator."""
    return (file_name or "").replace("%", "%25").replace("/", "%2F").replace("\\", "%5C")


def unescape_component(component):
    return component.replace("%5C", "\\").replace("%2F", "/").replace("%25", "%")


def storage_key(file_url):
    # file_url -> backend storage key. NOT always relative: upgraded sites stored
    # `?path=/<team>/<id>` and that slash is part of the S3 key. Callers building a
    # local path must lstrip("/") — `Path("a") / "/b" == Path("/b")`.
    file_url = str(file_url)
    if file_url.startswith(S3_URL_PREFIX):
        return unquote(file_url[len(S3_URL_PREFIX) :])
    return file_url.lstrip("/")


def stored_on_disk(file_url):
    """Whether a file_url (or storage key) names a blob on the site's disk.

    Framework-managed blobs (attachments, adopted uploads) keep their
    /private/files url and live on the site's disk even when Drive stores its
    own blobs on S3 — those always carry S3_URL_PREFIX or a bare bucket key.
    """
    return storage_key(file_url).startswith("private/files/")


def content_disposition(download_name):
    """RFC 6266 attachment header; non-ASCII names ride in RFC 5987 filename*
    (`secure_filename` would strip them to nothing)."""
    try:
        download_name.encode("ascii")
        names = {"filename": download_name}
    except UnicodeEncodeError:
        simple = unicodedata.normalize("NFKD", download_name).encode("ascii", "ignore").decode("ascii")
        quoted = quote(download_name, safe="!#$&+-.^_`|~")
        names = {"filename": simple, "filename*": f"UTF-8''{quoted}"}
    return dump_options_header("attachment", names)


def get_s3_key(file_url):
    prefixes = ["/private/files/", "/files/"]
    for prefix in prefixes:
        if file_url.startswith(prefix):
            return file_url[len(prefix) :]
    return file_url


def get_s3_url(path):
    from urllib.parse import quote

    return S3_URL_PREFIX + quote(path)
