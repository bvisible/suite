# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import annotations
import shutil
from pathlib import Path

import frappe
from frappe.model.document import Document

from suite.drive.utils import get_home_folder
from suite.drive.utils.files import get_s3_url, storage_key


class DriveTeam(Document):
    def after_insert(self):
        """Creates the file on disk"""
        self.ensure_root_folder()

        self.append("users", {"user": frappe.session.user, "access_level": 2})
        self.save()

    def ensure_root_folder(self):
        """Create this team's root folder if it does not have one yet.

        A team without a root folder is a team Drive cannot open at all:
        get_home_folder() finds nothing and throws "This team doesn't exist",
        which is misleading — the team is right there, it just has no root.

        Split out of after_insert so the same code can repair a team that
        already exists. Teams restored from a database backup are the usual
        case: the rows come back, after_insert never runs, and if the backup
        predates the drive -> suite migration the roots are still sitting in
        the legacy `tabDrive File` table that this site no longer has a DocType
        for. Measured on the Lite tenants (2026-08-04): every tenant cloned
        from the 2026-07-31 golden had all three of its teams unopenable.

        Idempotent: does nothing when a root is already there.
        """
        existing = frappe.db.get_value("File", {"team": self.name, "folder": ["in", ["", None]]}, "name")
        if existing:
            return existing

        d = frappe.get_doc(
            {
                "name": self.name,
                "doctype": "File",
                "file_name": f"Drive - {self.name}",
                "file_url": "",
                "is_folder": 1,
                "team": self.name,
            }
        )
        d.insert()

        settings = frappe.get_single("Drive Disk Settings")
        root_folder: str
        if self.s3_bucket:
            root_folder = self.prefix or ""
        else:
            root_folder = (
                Path(settings.root_folder)
                / {
                    settings.team_prefix == "team_id": self.name + "/",
                    settings.team_prefix == "team_name": f"{self.title} ({frappe.session.user})/",
                    settings.team_prefix == "none": "",
                }[True]
            )
        # file_url is the backend storage key (see storage_key/get_disk_path):
        # an S3 fetch URL for remote, else the on-disk path under private/files.
        d.file_url = get_s3_url(str(root_folder)) if self.s3_bucket else "/private/files/" + str(root_folder)
        d.save()

        # Create even with S3 as we need local folders before uploading to S3
        user_directory_path = Path(frappe.get_site_path("private/files")) / root_folder
        user_directory_path.mkdir(exist_ok=True, parents=True)  # allows prefixes to be nested
        (user_directory_path / ".uploads").mkdir(exist_ok=True)
        (user_directory_path / settings.thumbnail_prefix).mkdir(exist_ok=True)
        if settings.flat:
            (user_directory_path / "embeds").mkdir(exist_ok=True)

    def before_trash(self):
        try:
            site_dir = Path(frappe.get_site_path())
            files_dir = site_dir / "private" / "files"
            user_directory_path = site_dir / storage_key(get_home_folder(self.name).file_url)
            if user_directory_path != files_dir:
                shutil.rmtree(str(user_directory_path))
            frappe.db.delete("File", {"team": self.name})
        except:
            pass
