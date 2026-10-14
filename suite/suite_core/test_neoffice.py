# //// Neoffice — added file (no upstream equivalent): pins suite_core/neoffice.py,
# //// the fork decisions re-asserted at every migrate.
from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase

from suite.suite_core.neoffice import (
    PORTAL_ROLE,
    drop_orphan_role_assignments,
    drop_orphan_suite_role_assignments,
    ensure_portal_role_has_no_desk_access,
    ensure_wopi_secret,
)
from suite.tests.utils import ensure_user


class TestPortalRoleKeepsNoDeskAccess(IntegrationTestCase):
    """`suite/fixtures/role.json` states desk_access=0 on the signup role; a merge
    that restores upstream's 1 promotes every shop customer to System User."""

    def test_the_shipped_role_carries_no_desk_access(self):
        self.assertEqual(frappe.db.get_value("Role", PORTAL_ROLE, "desk_access"), 0)
        self.assertIs(ensure_portal_role_has_no_desk_access(), False, "must be a no-op")

    def test_a_role_that_came_back_with_desk_access_is_put_back(self):
        role = frappe.get_doc({"doctype": "Role", "role_name": f"Neoffice Test {frappe.generate_hash(6)}"})
        role.desk_access = 1
        role.insert(ignore_permissions=True)
        # ensure_portal_role_has_no_desk_access() commits, so this is undone by hand.
        self.addCleanup(self._drop_role, role.name)
        frappe.db.commit()

        self.assertIs(ensure_portal_role_has_no_desk_access(role.name), True)
        self.assertEqual(frappe.db.get_value("Role", role.name, "desk_access"), 0)

        self.assertIs(ensure_portal_role_has_no_desk_access(role.name), False, "idempotent")

    def test_an_orphan_assignment_does_not_abort_the_repair(self):
        """Role.on_update() does get_doc("User", …) on every holder and raises
        DoesNotExistError on the first row naming a deleted account. One such row is
        enough to take a whole `bench migrate` down — osiris carried two."""
        role = frappe.get_doc({"doctype": "Role", "role_name": f"Neoffice Test {frappe.generate_hash(6)}"})
        role.desk_access = 1
        role.insert(ignore_permissions=True)
        self.addCleanup(self._drop_role, role.name)

        ghost = f"deleted-{frappe.generate_hash(6)}@example.com"
        frappe.get_doc(
            {
                "doctype": "Has Role",
                "parenttype": "User",
                "parentfield": "roles",
                "parent": ghost,
                "role": role.name,
            }
        ).insert(ignore_permissions=True)
        frappe.db.commit()
        self.assertFalse(frappe.db.exists("User", ghost))

        self.assertIs(ensure_portal_role_has_no_desk_access(role.name), True)
        self.assertEqual(frappe.db.get_value("Role", role.name, "desk_access"), 0)
        self.assertEqual(
            frappe.get_all("Has Role", filters={"parenttype": "User", "role": role.name}, pluck="parent"),
            [],
            "the unreachable row must be gone, not merely stepped over",
        )

    def test_the_suite_roles_orphans_go_before_the_fixtures_sync(self):
        """The role fixture's import re-evaluates every holder; an orphan row made Frappe skip the whole file
        at every migrate (14.10.2026, the clone of osiris). A before_migrate hook, so it is ahead of the sync."""
        self.assertIn(
            "suite.suite_core.neoffice.drop_orphan_suite_role_assignments",
            frappe.get_hooks("before_migrate"),
        )

        ghost = f"deleted-{frappe.generate_hash(6)}@example.com"
        frappe.get_doc(
            {
                "doctype": "Has Role",
                "parenttype": "User",
                "parentfield": "roles",
                "parent": ghost,
                "role": PORTAL_ROLE,
            }
        ).insert(ignore_permissions=True)
        frappe.db.commit()

        self.assertGreaterEqual(drop_orphan_suite_role_assignments(), 1)
        self.assertFalse(frappe.db.exists("Has Role", {"parenttype": "User", "parent": ghost}))

    def test_dropping_orphans_leaves_the_live_assignments_alone(self):
        role = frappe.get_doc({"doctype": "Role", "role_name": f"Neoffice Test {frappe.generate_hash(6)}"})
        role.insert(ignore_permissions=True)
        self.addCleanup(self._drop_role, role.name)

        live = f"neoffice-role-{frappe.generate_hash(6)}@example.com"
        ensure_user(live)
        user = frappe.get_doc("User", live)
        user.append("roles", {"role": role.name})
        user.save(ignore_permissions=True)
        frappe.db.commit()

        self.assertEqual(drop_orphan_role_assignments(role.name), 0)
        self.assertEqual(
            frappe.get_all("Has Role", filters={"parenttype": "User", "role": role.name}, pluck="parent"),
            [live],
        )

    def _drop_role(self, name: str) -> None:
        frappe.db.delete("Has Role", {"parenttype": "User", "role": name})
        frappe.delete_doc("Role", name, force=True, ignore_permissions=True, delete_permanently=True)
        frappe.db.commit()


class TestNullFiltersMeanTheSameOnV15(IntegrationTestCase):
    """On Frappe v15 a filter `["!=", None]` renders `!= NULL`, which SQL never matches, while v16 reads it as
    "is set". Upstream writes it that way (14.10.2026: get_jmap_client, so every mailbox answered "no JMAP
    settings" on osiris); the fork spells it ["is", "set"], which both versions read the same."""

    def test_no_filter_of_the_app_compares_a_field_with_none(self):
        import os
        import re

        import suite

        root = os.path.dirname(suite.__file__)
        pattern = re.compile(r"""[\[(]\s*["'](?:!=|=|<>)["']\s*,\s*None\s*[\])]""")
        found = []
        for folder, folders, files in os.walk(root):
            folders[:] = [d for d in folders if d not in ("node_modules", "public", "__pycache__")]
            for name in files:
                if not name.endswith(".py") or name == "test_neoffice.py":
                    continue
                path = os.path.join(folder, name)
                with open(path, encoding="utf-8") as source:
                    for number, line in enumerate(source, 1):
                        # the notes that explain the idiom quote it
                        if not line.lstrip().startswith("#") and pattern.search(line):
                            found.append(f"{os.path.relpath(path, root)}:{number}")

        self.assertEqual(found, [], "use [\"is\", \"set\"] / [\"is\", \"not set\"], which v15 and v16 read alike")

    def test_a_user_whose_settings_carry_a_username_reaches_the_mail_server(self):
        """The real lookup, unmocked: the settings row is found once it has a username, not before."""

        from unittest import mock

        from suite.mail import jmap as suite_jmap

        class Reached(Exception):
            pass

        user = f"jmap-settings-{frappe.generate_hash(6)}@example.com"
        ensure_user(user)
        settings = frappe.db.get_value("User Settings", {"user": user})
        self.assertTrue(settings, "User Settings come with the user")

        settings_doc = mock.Mock(username="mailbox@example.com")
        settings_doc.get_password.return_value = "pw"

        def get_client():
            frappe.local.request_cache.clear()  # get_jmap_client is cached per request
            with (
                mock.patch.object(suite_jmap, "get_config", return_value=("https://jmap.example.com", 1)),
                mock.patch.object(suite_jmap, "get_cached_session", return_value=None),
                mock.patch.object(suite_jmap.SuiteJMAPClient, "connect", side_effect=Reached),
                mock.patch.object(frappe, "get_cached_doc", return_value=settings_doc),
            ):
                return suite_jmap.get_jmap_client(user, ignore_permissions=True)

        def set_username(value):
            frappe.db.set_value("User Settings", settings, "username", value, update_modified=False)

        set_username(None)
        with self.assertRaises(frappe.ValidationError):
            get_client()

        set_username("mailbox@example.com")
        with self.assertRaises(Reached):
            get_client()


class TestWopiSecretIsProvisionedOnce(IntegrationTestCase):
    """The signing secret has one source of truth. It used to be minted per request,
    inside a try/except that swallowed the write on every read-only transaction."""

    def test_it_is_a_no_op_when_the_secret_is_readable(self):
        self.assertTrue(frappe.get_single("WOPI Settings").get_password("jwt_secret"))
        self.assertIs(ensure_wopi_secret(), False)

    def test_it_provisions_a_missing_secret_and_only_once(self):
        original = frappe.get_single("WOPI Settings").get_password("jwt_secret")
        self.addCleanup(self._restore_secret, original)

        settings = frappe.get_single("WOPI Settings")
        settings.db_set("jwt_secret", None)
        frappe.db.commit()

        self.assertIs(ensure_wopi_secret(), True)
        minted = frappe.get_single("WOPI Settings").get_password("jwt_secret")
        self.assertTrue(minted)
        self.assertNotEqual(minted, original)

        self.assertIs(ensure_wopi_secret(), False, "idempotent")
        self.assertEqual(frappe.get_single("WOPI Settings").get_password("jwt_secret"), minted)

    def _restore_secret(self, original: str) -> None:
        settings = frappe.get_single("WOPI Settings")
        settings.jwt_secret = original
        settings.save(ignore_permissions=True)
        frappe.db.commit()
