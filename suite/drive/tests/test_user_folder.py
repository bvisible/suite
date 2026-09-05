# //// Neoffice — added file (no upstream equivalent). get_user_folder() is upstream
# //// code; it addressed `Drive Settings` by name, which stops being the user's
# //// address the moment that User is renamed. This pins the fix.
from __future__ import annotations

import shutil

import frappe
from frappe.tests import IntegrationTestCase

from suite.drive.utils import get_user_folder
from suite.drive.utils.files import FileManager, storage_key
from suite.tests.utils import ensure_user


class TestUserFolderAfterARename(IntegrationTestCase):
    """`Drive Settings` autonames `field:user`. A rename cascades into the `user`
    LINK field but leaves the row named after the old address, so every lookup by
    name missed: the user got a SECOND private folder, and the function then died on
    the unique index of `user` — after the orphan had been created and shared."""

    def setUp(self):
        frappe.flags.mute_drive_activity_log = True
        suffix = frappe.generate_hash(6)
        self.old = f"drive-rename-{suffix}@example.com"
        self.new = f"drive-renamed-{suffix}@example.com"
        ensure_user(self.old)
        ensure_user(self.new)

    def tearDown(self):
        frappe.flags.mute_drive_activity_log = False
        super().tearDown()

    def _forget_folder_on_disk(self, file_url: str) -> None:
        shutil.rmtree(FileManager().site_folder / storage_key(file_url), ignore_errors=True)

    def _leave_the_state_a_rename_leaves(self) -> None:
        """Reproduce what ``rename_doc("User", old, new)`` leaves behind.

        The rename itself is deliberately not run here. ``User.validate`` calls
        ``ask_pass_update()``, which rewrites the site-wide ``email_user_password``
        default; holding that one row for the length of a User rename deadlocks
        against the background workers of a live instance (measured on osiris,
        04.09.2026, "Lock wait timeout exceeded"). What ``get_user_folder`` sees is
        the state, and this is exactly it — Frappe cascades a rename into every LINK
        field pointing at User, ``Drive Settings.user`` included, and never renames
        the row carrying it.
        """
        frappe.delete_doc(
            "Drive Settings", self.new, force=True, ignore_permissions=True, delete_permanently=True
        )
        frappe.db.set_value("Drive Settings", self.old, "user", self.new, update_modified=False)

        self.assertEqual(
            frappe.db.get_value("Drive Settings", {"user": self.new}, "name"),
            self.old,
            "precondition of the bug: the row keeps its old name",
        )

    def test_the_renamed_user_keeps_the_folder_they_already_had(self):
        before = get_user_folder(self.old)
        self.addCleanup(self._forget_folder_on_disk, before.file_url)

        self._leave_the_state_a_rename_leaves()

        after = get_user_folder(self.new)

        self.assertEqual(after.name, before.name, "a second, orphan folder was created")
        self.assertEqual(frappe.db.count("Drive Settings", {"user": self.new}), 1)

    def test_calling_it_twice_after_a_rename_does_not_raise(self):
        before = get_user_folder(self.old)
        self.addCleanup(self._forget_folder_on_disk, before.file_url)

        self._leave_the_state_a_rename_leaves()

        # Before the fix the call reached the final insert and died there on
        # DuplicateEntryError, every single time.
        self.assertEqual(get_user_folder(self.new).name, get_user_folder(self.new).name)
