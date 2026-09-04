#//// Neoffice — added file (no upstream equivalent): pins suite_core/neoffice.py,
#//// the fork decisions re-asserted at every migrate.
from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase

from suite.suite_core.neoffice import ensure_wopi_secret


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
