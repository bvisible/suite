# //// Neoffice — added file (no upstream equivalent): the cross-site paths into Mail, Calendar and Contacts — writes
# //// reachable by a GET, forged pushes, and what the mail screens draw from a sender's text (neoffice-maintenance#2296).
"""Mail, Calendar and Contacts against a page or a sender who is not the user.

- A state change (sieve scripts, mailboxes, calendars, contacts...) answers POST only: frappe checks the CSRF
  token on every method but GET, and a cross-site link or image is a GET.
- The open JMAP push endpoint acts only on the accounts linked to the user it names.
- The mail screens escape the sender's names, subject and file names, open attachments and links without handing
  the sender a script or an opener, and block remote content whatever the markup.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote

import frappe
from frappe.handler import is_valid_http_method
from frappe.tests import UnitTestCase
from frappe.tests.roles import as_role
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from suite.mail.api import jmap as jmap_api

FRONTEND = Path(frappe.get_app_path("suite")).parent / "frontend" / "src" / "apps"

POST_ONLY = [
    ("suite.mail.api.account", None, "create_mail_import"),
    ("suite.mail.api.account", None, "create_mail_export"),
    ("suite.mail.api.account", None, "create_calendar_import"),
    ("suite.mail.api.account", None, "create_calendar_export"),
    ("suite.mail.api.account", None, "create_contacts_import"),
    ("suite.mail.api.account", None, "create_contacts_export"),
    ("suite.mail.api.account", None, "set_signature"),
    ("suite.mail.api.mail", None, "create_mail"),
    ("suite.mail.api.mail", None, "update_draft_mail"),
    ("suite.mail.api.mail", None, "delete_mail"),
    ("suite.mail.api.mail", None, "set_flagged"),
    ("suite.mail.api.mail", None, "set_mails_seen"),
    ("suite.mail.api.mail", None, "move_mails"),
    ("suite.mail.api.mail", None, "add_mails_to_mailbox"),
    ("suite.mail.api.mail", None, "remove_mails_from_mailbox"),
    ("suite.mail.api.mail", None, "set_mails_mailboxes"),
    ("suite.mail.api.mail", None, "set_mails_spam_status"),
    ("suite.mail.api.mail", None, "empty_user_mailbox"),
    ("suite.mail.api.mail", None, "create_mailbox"),
    ("suite.mail.api.mail", None, "update_mailbox"),
    ("suite.mail.api.mail", None, "delete_mailbox"),
    ("suite.mail.api.mail", None, "screen_email_address"),
    ("suite.mail.api.mail", None, "screen_email_addresses"),
    ("suite.mail.api.mail", None, "unscreen_email_addresses"),
    ("suite.mail.api.mail", None, "allow_screening_senders"),
    ("suite.mail.api.mail", None, "move_screening_mails_to_inbox"),
    ("suite.mail.api.mail", None, "screen_out_senders"),
    ("suite.mail.api.mail", None, "undo_screening_verdict"),
    ("suite.calendar.api", None, "create_calendar"),
    ("suite.calendar.api", None, "edit_calendar"),
    ("suite.calendar.api", None, "delete_calendar"),
    ("suite.calendar.api", None, "rsvp_calendar_event"),
    ("suite.calendar.api", None, "edit_calendar_event"),
    ("suite.calendar.api", None, "split_calendar_event_series"),
    ("suite.calendar.api", None, "delete_calendar_event_series_from"),
    ("suite.calendar.api.invites", None, "add_invite_to_calendar"),
    ("suite.calendar.api.invites", None, "rsvp_to_invite"),
    ("suite.calendar.doctype.calendar.calendar", None, "bulk_delete"),
    ("suite.calendar.doctype.calendar.calendar", None, "add_calendar"),
    ("suite.calendar.doctype.calendar.calendar", None, "update_calendar"),
    ("suite.calendar.doctype.calendar.calendar", None, "delete_calendars"),
    ("suite.calendar.doctype.calendar.calendar", None, "share_calendar"),
    ("suite.calendar.doctype.calendar.calendar", None, "set_calendar_visibility"),
    ("suite.calendar.doctype.calendar_event.calendar_event", None, "bulk_delete"),
    ("suite.calendar.doctype.calendar_event.calendar_event", None, "add_calendar_event"),
    ("suite.calendar.doctype.calendar_event.calendar_event", None, "update_calendar_event"),
    ("suite.calendar.doctype.calendar_event.calendar_event", None, "update_calendar_event_instance"),
    ("suite.calendar.doctype.calendar_event.calendar_event", None, "delete_calendar_events"),
    ("suite.calendar.doctype.calendar_event.calendar_event", None, "delete_calendar_event_instance"),
    ("suite.calendar.doctype.calendar_exchange.calendar_exchange", "CalendarExchange", "retry"),
    ("suite.calendar.doctype.event_notification.event_notification", None, "bulk_delete"),
    ("suite.calendar.doctype.event_notification.event_notification", None, "delete_event_notifications"),
    ("suite.calendar.feed", None, "enable_calendar_feed"),
    ("suite.calendar.feed", None, "regenerate_calendar_feed"),
    ("suite.calendar.feed", None, "disable_calendar_feed"),
    ("suite.calendar.local", None, "ensure_local_calendar_account"),
    ("suite.calendar.sources", None, "set_calendar_scope"),
    ("suite.mail.api.scheduled", None, "reschedule_mail"),
    ("suite.mail.api.scheduled", None, "send_scheduled_mail_now"),
    ("suite.mail.api.scheduled", None, "cancel_scheduled_mail"),
    ("suite.mail.api.scheduled", None, "retry_failed_mail"),
    ("suite.mail.api.scheduled", None, "dismiss_failed_mail"),
    ("suite.mail.api.sieve", None, "create_sieve_script"),
    ("suite.mail.api.sieve", None, "update_sieve_script"),
    ("suite.mail.api.sieve", None, "delete_sieve_script"),
    ("suite.mail.api.sieve", None, "create_automation_script"),
    ("suite.mail.api.sieve", None, "rebuild_automation_script_for_account"),
    ("suite.mail.doctype.address_book.address_book", None, "bulk_delete"),
    ("suite.mail.doctype.address_book.address_book", None, "add_address_book"),
    ("suite.mail.doctype.address_book.address_book", None, "update_address_book"),
    ("suite.mail.doctype.address_book.address_book", None, "delete_address_books"),
    ("suite.mail.doctype.contact_card.contact_card", None, "bulk_delete"),
    ("suite.mail.doctype.contact_card.contact_card", None, "add_contact_card"),
    ("suite.mail.doctype.contact_card.contact_card", None, "bulk_add_contact_cards"),
    ("suite.mail.doctype.contact_card.contact_card", None, "update_contact_card"),
    ("suite.mail.doctype.contact_card.contact_card", None, "contact_card_add_to_address_book"),
    ("suite.mail.doctype.contact_card.contact_card", None, "contact_card_remove_from_address_book"),
    ("suite.mail.doctype.contact_card.contact_card", None, "contact_card_move_between_address_books"),
    ("suite.mail.doctype.contact_card.contact_card", None, "contact_card_move_to_address_book"),
    ("suite.mail.doctype.contact_card.contact_card", None, "delete_contact_cards"),
    ("suite.mail.doctype.contacts_exchange.contacts_exchange", "ContactsExchange", "retry"),
    ("suite.mail.doctype.identity.identity", None, "bulk_delete"),
    ("suite.mail.doctype.identity.identity", None, "add_identity"),
    ("suite.mail.doctype.identity.identity", None, "update_identity"),
    ("suite.mail.doctype.identity.identity", None, "delete_identities"),
    ("suite.mail.doctype.jmap_account.jmap_account", "JMAPAccount", "clear_cached_jmap_identities"),
    ("suite.mail.doctype.jmap_account.jmap_account", "JMAPAccount", "clear_cached_jmap_mailboxes"),
    ("suite.mail.doctype.jmap_account.jmap_account", "JMAPAccount", "clear_cached_blobs"),
    ("suite.mail.doctype.jmap_account.jmap_account", "JMAPAccount", "clear_cached_mail_messages"),
    ("suite.mail.doctype.jmap_account.jmap_account", "JMAPAccount", "clear_cached_contact_cards"),
    ("suite.mail.doctype.jmap_account.jmap_account", "JMAPAccount", "clear_search_indexes"),
    ("suite.mail.doctype.jmap_account.jmap_account", "JMAPAccount", "rebuild_search_index"),
    ("suite.mail.doctype.mail_exchange.mail_exchange", "MailExchange", "retry"),
    ("suite.mail.doctype.mail_message.mail_message", "MailMessage", "save_draft"),
    ("suite.mail.doctype.mail_message.mail_message", "MailMessage", "submit"),
    ("suite.mail.doctype.mail_message.mail_message", "MailMessage", "move_to_mailbox"),
    ("suite.mail.doctype.mail_message.mail_message", "MailMessage", "add_to_mailbox"),
    ("suite.mail.doctype.mail_message.mail_message", "MailMessage", "remove_from_mailbox"),
    ("suite.mail.doctype.mail_message.mail_message", "MailMessage", "set_seen"),
    ("suite.mail.doctype.mail_message.mail_message", "MailMessage", "set_flagged"),
    ("suite.mail.doctype.mail_message.mail_message", "MailMessage", "reply"),
    ("suite.mail.doctype.mail_message.mail_message", "MailMessage", "reply_all"),
    ("suite.mail.doctype.mail_message.mail_message", "MailMessage", "forward"),
    ("suite.mail.doctype.mail_message.mail_message", None, "bulk_delete"),
    ("suite.mail.doctype.mail_message.mail_message", None, "reply"),
    ("suite.mail.doctype.mail_message.mail_message", None, "reply_all"),
    ("suite.mail.doctype.mail_message.mail_message", None, "forward"),
    ("suite.mail.doctype.mail_queue.mail_queue", "MailQueue", "retry"),
    ("suite.mail.doctype.mail_queue.mail_queue", None, "bulk_retry"),
    ("suite.mail.doctype.mail_settings.mail_settings", "MailSettings", "generate_jmap_push_keys"),
    ("suite.mail.doctype.mailbox.mailbox", None, "bulk_delete"),
    ("suite.mail.doctype.mailbox.mailbox", None, "add_mailbox"),
    ("suite.mail.doctype.mailbox.mailbox", None, "update_mailbox"),
    ("suite.mail.doctype.mailbox.mailbox", None, "delete_mailboxes"),
    ("suite.mail.doctype.mailbox.mailbox", None, "update_mailbox_position"),
    ("suite.mail.doctype.participant_identity.participant_identity", None, "bulk_delete"),
    ("suite.mail.doctype.participant_identity.participant_identity", None, "add_participant_identity"),
    ("suite.mail.doctype.participant_identity.participant_identity", None, "update_participant_identity"),
    ("suite.mail.doctype.participant_identity.participant_identity", None, "delete_participant_identities"),
    ("suite.mail.doctype.push_subscription.push_subscription", "PushSubscription", "renew"),
    ("suite.mail.doctype.push_subscription.push_subscription", None, "bulk_delete"),
    ("suite.mail.doctype.push_subscription.push_subscription", None, "add_push_subscription"),
    ("suite.mail.doctype.push_subscription.push_subscription", None, "renew_push_subscription"),
    ("suite.mail.doctype.push_subscription.push_subscription", None, "delete_push_subscriptions"),
    ("suite.mail.doctype.sieve_script.sieve_script", None, "bulk_delete"),
    ("suite.mail.doctype.sieve_script.sieve_script", None, "rebuild_all_automation_sieves"),
    ("suite.mail.doctype.vacation_response.vacation_response", None, "update_vacation_response"),
    ("suite.mail.events", None, "ensure_personal_mail_account"),
    ("suite.mail.events", None, "provision_existing_mail_accounts"),
    ("suite.mail.store", None, "destroy_data_store"),
    ("suite.mail.store", None, "destroy_blob_store"),
    ("suite.mail.store", None, "destroy_search_index"),
    ("suite.mail.store", None, "rebuild_all_email_address_indexes"),
]


def endpoint(module: str, cls: str | None, name: str):
    owner = frappe.get_module(module)
    return getattr(getattr(owner, cls), name) if cls else getattr(owner, name)


class RequestAs:
    """A request of the given method, as frappe.local.request, for the time of a block."""

    def __init__(self, method: str, path: str = "/api/method/x", **kwargs):
        self.request = Request(EnvironBuilder(path=path, method=method, **kwargs).get_environ())

    def __enter__(self):
        self.previous = getattr(frappe.local, "request", None)
        frappe.local.request = self.request
        return self.request

    def __exit__(self, *exc):
        if self.previous is None:
            del frappe.local.request
        else:
            frappe.local.request = self.previous


class TestWritesArePostOnly(UnitTestCase):
    def test_every_write_endpoint_answers_post_only(self):
        for module, cls, name in POST_ONLY:
            with self.subTest(endpoint=f"{module}.{cls + '.' if cls else ''}{name}"):
                fn = endpoint(module, cls, name)
                self.assertEqual(list(frappe.allowed_http_methods_for_whitelisted_func[fn]), ["POST"])

    def test_a_cross_site_get_is_refused_before_the_body_runs(self):
        fn = endpoint("suite.mail.api.sieve", None, "create_sieve_script")
        with as_role("sales_user"), RequestAs("GET"), self.assertRaises(frappe.PermissionError):
            is_valid_http_method(fn)
        with as_role("sales_user"), RequestAs("POST"):
            is_valid_http_method(fn)


class TestPushNotification(UnitTestCase):
    user = "mailbox-owner@example.test"

    def push(self, payload: dict, linked: set[str]):
        with (
            as_role("Guest"),
            RequestAs(
                "POST",
                path="/api/method/suite.mail.api.jmap.push_notification",
                query_string={"user": quote(self.user)},
                data=json.dumps(payload),
                content_type="application/json",
            ),
            patch.object(jmap_api, "get_push_subscription_keys", return_value=None),
            patch.object(jmap_api, "is_jmap_push_notifications_frozen", return_value=False),
            patch.object(
                jmap_api,
                "is_jmap_account_belongs_to_user",
                side_effect=lambda account, user: user == self.user and account in linked,
            ),
            patch.object(jmap_api, "enqueue_fetch_changes") as fetch,
            patch.object(jmap_api, "invalidate_jmap_mailboxes_cache") as mailboxes,
            patch.object(jmap_api, "invalidate_jmap_identities_cache") as identities,
            patch.object(jmap_api, "enqueue_send_event_alert_notification") as alert,
        ):
            result = jmap_api.push_notification()
        return result, fetch, mailboxes, identities, alert

    def test_a_push_naming_accounts_of_someone_else_does_nothing(self):
        payload = {
            "@type": "StateChange",
            "changed": {
                "other-1": {"Email": "s1", "Mailbox": "m1", "Identity": "i1"},
                "other-2": {"Email": "s2"},
            },
        }
        result, fetch, mailboxes, identities, _ = self.push(payload, linked={"own"})
        self.assertEqual(result["status"], "processed")
        fetch.assert_not_called()
        mailboxes.assert_not_called()
        identities.assert_not_called()

    def test_a_push_for_the_users_own_account_still_syncs(self):
        payload = {"@type": "StateChange", "changed": {"own": {"Email": "s1", "Mailbox": "m1"}}}
        _, fetch, mailboxes, _, _ = self.push(payload, linked={"own"})
        self.assertEqual(fetch.call_args.args[:3], (self.user, "own", "s1"))
        mailboxes.assert_called_once_with("own")

    def test_a_calendar_alert_for_an_unlinked_account_is_dropped(self):
        payload = {"@type": "CalendarAlert", "accountId": "other-1", "calendarEventId": "e1", "uid": "u1"}
        _, _, _, _, alert = self.push(payload, linked={"own"})
        alert.assert_not_called()
        payload["accountId"] = "own"
        _, _, _, _, alert = self.push(payload, linked={"own"})
        alert.assert_called_once()


class TestMailScreens(UnitTestCase):
    """The frontend fixes, read from the source (the built bundle is made from it in CI)."""

    def read(self, path: str) -> str:
        return (FRONTEND / path).read_text()

    def test_attachment_print_escapes_the_file_name(self):
        source = self.read("mail/components/AttachmentViewer.vue")
        self.assertNotIn("<title>${currentAttachment.value?.filename", source)
        self.assertIn("escapeHtml(currentAttachment.value?.filename || 'Print')", source)

    def test_forward_and_quote_headers_escape_the_senders_text(self):
        source = self.read("mail/components/MailThread.vue")
        header = source[source.index("const getForwardHeader") : source.index("const getForwardedBody")]
        for raw in ("[mail.subject || '']", "[recipients.to]", "[recipients.cc]", "${mail.from_name}"):
            self.assertNotIn(raw, header)
        for escaped in (
            "headerText(mail.subject)",
            "headerText(recipients.to)",
            "headerText(mail.from_name)",
        ):
            self.assertIn(escaped, header)
        self.assertIn("headerText(mail.from_email)])}", source)

    def test_an_attachment_opens_in_a_tab_only_as_a_type_that_cannot_script(self):
        source = self.read("mail/composables/useComposeMail.ts")
        self.assertIn("getAttachmentUrl(blob_id, inlineSafeType(type)", source)
        pattern = re.search(r"const INLINE_SAFE_TYPE = /(.+)/i\n", source).group(1)
        allowed = re.compile(pattern, re.I)
        for kept in ("image/png", "image/jpeg", "application/pdf", "text/plain", "video/mp4", "audio/mpeg"):
            self.assertTrue(allowed.match(kept), kept)
        for refused in (
            "text/html",
            "image/svg+xml",
            "application/xhtml+xml",
            "text/xml",
            "application/javascript",
        ):
            self.assertFalse(allowed.match(refused), refused)

    def test_the_mail_frame_takes_messages_from_itself_and_opens_links_without_an_opener(self):
        source = self.read("mail/components/EmailContent.vue")
        handler = source[source.index("const handleMessage") : source.index("onMounted(")]
        first = handler.index(
            "event.source !== (frame.value?.$el as HTMLIFrameElement | undefined)?.contentWindow"
        )
        self.assertLess(first, handler.index("type === 'swipe'"))
        self.assertLess(first, handler.index("!== 'keyboard'"))
        self.assertIn("window.open(anchor.href, '_blank', 'noopener,noreferrer')", source)
        event = self.read("calendar/components/EventDetail.vue")
        self.assertIn("window.open(location, '_blank', 'noopener,noreferrer')", event)

    def test_remote_content_is_blocked_by_a_policy_and_a_refresh_never_runs(self):
        source = self.read("mail/components/EmailContent.vue")
        self.assertIn("effectiveBlock.value ? remoteContentPolicy() : ''", source)
        self.assertIn("\"default-src 'none'\"", source)
        self.assertIn('<meta http-equiv="Content-Security-Policy"', source)
        self.assertIn("doc.querySelectorAll('meta[http-equiv]')", source)
        self.assertIn("refresh", source[source.index("meta[http-equiv]") :][:200])
