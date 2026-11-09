# //// Neoffice — added file (no upstream equivalent). Holds neoffice-maintenance#2396: the disk quota of a new mailbox
# //// was read in the arguments of `create_account`, inside the loop that looks for a free name, so a missing
# //// configuration key was logged 30 times as a name collision. No network: Stalwart and the configuration are replaced.

import unittest
from unittest.mock import MagicMock, patch

from suite.mail import events


class TestTheQuotaOfANewMailboxIsReadOnce(unittest.TestCase):
    def _provision(self, get_config, create_app_password_effect=None):
        with (
            patch.object(events.frappe, "get_doc", return_value=MagicMock(email="a@x.test", full_name="A")),
            patch.object(events, "_should_provision_mail", return_value=True),
            patch("suite.mail.neoffice_stalwart.get_domains", return_value=[{"name": "mail.test"}]),
            patch("suite.mail.neoffice_stalwart.create_account") as create_account,
            patch("suite.mail.neoffice_stalwart.create_app_password", side_effect=create_app_password_effect),
            patch("suite.mail.utils.get_config", side_effect=get_config),
            patch.object(events.frappe, "log_error") as log_error,
            patch.object(events.frappe.db, "exists", return_value=False),
        ):
            try:
                events._provision_mail_account_now("a@x.test")
            except RuntimeError:
                pass  # the test stops the run after the account is created
        return create_account, log_error

    def test_a_missing_quota_key_is_said_once_and_no_account_is_attempted(self):
        def missing(key):
            raise Exception(f"Mail config key '{key}' not found")

        create_account, log_error = self._provision(missing)
        create_account.assert_not_called()
        self.assertEqual(log_error.call_count, 1)
        self.assertEqual(log_error.call_args.args[0], "Mail auto-provision not configured")

    def test_a_configured_quota_reaches_the_account_and_the_key_is_read_once(self):
        reads = []

        def configured(key):
            reads.append(key)
            return 5

        create_account, log_error = self._provision(configured, RuntimeError("stop"))
        self.assertEqual(reads, ["default_disk_quota_gb"])
        create_account.assert_called_once()
        self.assertEqual(create_account.call_args.kwargs["quota"], 5 * 1024**3)
        log_error.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
