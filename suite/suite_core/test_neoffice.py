# //// Neoffice — added file (no upstream equivalent): pins suite_core/neoffice.py,
# //// the fork decisions re-asserted at every migrate.
from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase

from suite.suite_core.neoffice import (
    PORTAL_ROLE,
    drop_orphan_role_assignments,
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
