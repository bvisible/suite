# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from . import __version__ as app_version

# ============================================================================
# App metadata (Suite)
# ============================================================================
app_name = "suite"
app_title = "Frappe Suite"
app_publisher = "Frappe"
app_description = "Frappe Suite"
app_email = "developers@frappe.io"
app_license = "agpl-3.0"

# ============================================================================
# Apps screen / App switcher
# ============================================================================
add_to_apps_screen = [
    {
        "name": "suite",
        "logo": "/assets/suite/frontend/logo.svg",
        "title": "Frappe Suite",
        "route": "/suite",
    },
]

# ============================================================================
# Includes
# ============================================================================
# drive
app_include_js = ["ff_integration.bundle.js"]

# drive — include js in doctype views (File form tweaks)
doctype_js = {"File": "public/js/file.js"}

# mail — email-specific Tailwind CSS for email template rendering
email_css = ["/assets/suite/mail/css/email.css"]

# writer — SQLite full-text search provider
sqlite_search = ["suite.writer.search.WriterSearch"]

# ============================================================================
# Website routing (concatenated from all apps)
# ============================================================================
# Unified SPA: every former-app prefix serves the single suite bootstrap
# (www/suite.py -> suite.html); Vue Router takes over client-side. (plan D9)
# Both the bare prefix and the sub-path are mapped so deep links + launcher
# links (which use the bare prefix) both hit the SPA on first load.
website_route_rules = [
    {"from_route": "/suite/<path:app_path>", "to_route": "suite"},
    {"from_route": "/drive", "to_route": "suite"},
    {"from_route": "/drive/<path:app_path>", "to_route": "suite"},
    {"from_route": "/slides", "to_route": "suite"},
    {"from_route": "/slides/<path:app_path>", "to_route": "suite"},
    {"from_route": "/sheets", "to_route": "suite"},
    {"from_route": "/sheets/<path:app_path>", "to_route": "suite"},
    {"from_route": "/writer", "to_route": "suite"},
    {"from_route": "/writer/<path:app_path>", "to_route": "suite"},
    {"from_route": "/mail", "to_route": "suite"},
    {"from_route": "/mail/<path:app_path>", "to_route": "suite"},
    {"from_route": "/meet", "to_route": "suite"},
    {"from_route": "/meet/<path:app_path>", "to_route": "suite"},
    {"from_route": "/calendar", "to_route": "suite"},
    {"from_route": "/calendar/<path:app_path>", "to_route": "suite"},
    # //// Neoffice — WOPI callbacks for Collabora Online. Upstream has no
    # //// Office-document editing at all; we route documents to a Collabora
    # //// server over the WOPI protocol, which needs these two public routes
    # //// (the host calls them back with a token). See suite/drive/wopi/.
    {"from_route": "/wopi/files/<file_id>", "to_route": "wopi_handler"},
    {"from_route": "/wopi/files/<file_id>/contents", "to_route": "wopi_handler"},
]

home_page = "suite"

# mail — website redirects
website_redirects = [
    # //// Neoffice — there must be NO "/" -> "/suite" redirect here. Upstream
    # //// dropped it too (this list matches theirs), but it has come back before:
    # //// frappe/mail is a desk-first product that owns its domain root, whereas a
    # //// Neoffice instance serves a public website there (webshop / builder pages).
    # //// The rule hijacked the root of dmis.ch and the site vitrine vanished behind
    # //// the Suite SPA. If a merge ever brings it back, drop it again.
    {
        "source": "/auth/validate",
        "target": "/api/method/suite.mail.api.auth.validate",
        "redirect_http_status": 307,
    },
    {
        "source": "/outbound/upload",
        "target": "/api/method/suite.mail.api.outbound.upload_attachment",
        "redirect_http_status": 307,
    },
    {
        "source": "/outbound/send",
        "target": "/api/method/suite.mail.api.outbound.send",
        "redirect_http_status": 307,
    },
    {
        "source": "/outbound/send-raw",
        "target": "/api/method/suite.mail.api.outbound.send_raw",
        "redirect_http_status": 307,
    },
    {
        "source": "/inbound/blob",
        "target": "/api/method/suite.mail.api.inbound.fetch_blob",
        "redirect_http_status": 307,
    },
    {
        "source": "/inbound/pull",
        "target": "/api/method/suite.mail.api.inbound.pull",
        "redirect_http_status": 307,
    },
    {
        "source": "/inbound/pull-raw",
        "target": "/api/method/suite.mail.api.inbound.pull_raw",
        "redirect_http_status": 307,
    },
    {
        "source": "/spamd/scan",
        "target": "/api/method/suite.mail.api.spamd.scan",
        "redirect_http_status": 307,
    },
    {
        "source": "/spamd/score",
        "target": "/api/method/suite.mail.api.spamd.get_spam_score",
        "redirect_http_status": 307,
    },
]

# Framework File permission logic is fully replaced by Drive's
ignore_file_permissions = True

# ============================================================================
# Permissions — permission_query_conditions (deep-merged union; no key clashes)
# ============================================================================
permission_query_conditions = {
    # drive
    "File": "suite.drive.utils.overrides.filter_file",
    "Drive Permission": "suite.drive.utils.overrides.filter_drive_permission",
    "Drive Settings": "suite.drive.utils.overrides.filter_drive_settings",
    "Drive User Invitation": "suite.drive.utils.overrides.filter_drive_invitation",
    "Drive Entity Activity Log": "suite.drive.utils.overrides.filter_activity_log",
    "Drive Favourite": "suite.drive.utils.overrides.filter_drive_favourite",
    "Drive Entity Log": "suite.drive.utils.overrides.filter_drive_recent",
    "Drive Notification": "suite.drive.utils.overrides.filter_drive_notif",
    # slides
    "Presentation": "suite.slides.doctype.presentation.presentation.get_permission_query_conditions",
    # writer
    "Writer Template": "suite.writer.overrides.filter_templates",
    "Writer Document": "suite.writer.overrides.document_query_conditions",
    "Writer Version": "suite.writer.overrides.version_query_conditions",
    # sheets
    "Sheet Op Log": "suite.sheets.permissions.sheet_op_log_query",
    "Sheet Snapshot": "suite.sheets.permissions.sheet_snapshot_query",
    # meet
    "Meet Room": "suite.meet.doctype.meet_room.meet_room.get_permission_query_conditions",
    "Meet Recording": "suite.meet.doctype.meet_recording.meet_recording.get_permission_query_conditions",
    # mail
    "JMAP Account": "suite.mail.doctype.jmap_account.jmap_account.get_permission_query_condition",
    "Mail Sync History": "suite.mail.doctype.mail_sync_history.mail_sync_history.get_permission_query_condition",
    "Mailbox Settings": "suite.mail.doctype.mailbox_settings.mailbox_settings.get_permission_query_condition",
    "Screened Email Address": "suite.mail.doctype.screened_email_address.screened_email_address.get_permission_query_condition",
}

# ============================================================================
# Permissions — has_permission (deep-merged union; no key clashes)
# ============================================================================
has_permission = {
    # drive
    "File": "suite.drive.api.permissions.user_has_permission",
    "Drive Permission": "suite.drive.api.permissions.drive_permission_has_permission",
    "Drive Entity Activity Log": "suite.drive.api.permissions.activity_log_has_permission",
    "Drive Settings": "suite.drive.api.permissions.drive_settings_has_permission",
    "Drive User Invitation": "suite.drive.api.permissions.drive_invitation_has_permission",
    # slides
    "Presentation": "suite.slides.doctype.presentation.presentation.has_permission",
    # writer
    "Writer Document": "suite.drive.overrides.file.content_has_permission",
    "Writer Version": "suite.writer.overrides.version_has_permission",
    "Writer Template": "suite.writer.overrides.template_has_permission",
    # sheets
    "Sheet Op Log": "suite.sheets.permissions.sheet_op_log_has_permission",
    "Sheet Snapshot": "suite.sheets.permissions.sheet_snapshot_has_permission",
    # meet
    "Meet Room": "suite.meet.doctype.meet_room.meet_room.has_permission",
    "Meet Recording": "suite.meet.doctype.meet_recording.meet_recording.has_permission",
    # mail
    "JMAP Account": "suite.mail.doctype.jmap_account.jmap_account.has_permission",
    "Address Book": "suite.mail.doctype.address_book.address_book.has_permission",
    "Calendar": "suite.calendar.doctype.calendar.calendar.has_permission",
    "Calendar Event": "suite.calendar.doctype.calendar_event.calendar_event.has_permission",
    "Contact Card": "suite.mail.doctype.contact_card.contact_card.has_permission",
    "Event Notification": "suite.calendar.doctype.event_notification.event_notification.has_permission",
    "Identity": "suite.mail.doctype.identity.identity.has_permission",
    "Mail Sync History": "suite.mail.doctype.mail_sync_history.mail_sync_history.has_permission",
    "Mailbox": "suite.mail.doctype.mailbox.mailbox.has_permission",
    "Mailbox Settings": "suite.mail.doctype.mailbox_settings.mailbox_settings.has_permission",
    "Participant Identity": "suite.mail.doctype.participant_identity.participant_identity.has_permission",
    "Push Subscription": "suite.mail.doctype.push_subscription.push_subscription.has_permission",
    "Quota": "suite.mail.doctype.quota.quota.has_permission",
    "Screened Email Address": "suite.mail.doctype.screened_email_address.screened_email_address.has_permission",
    "Sieve Script": "suite.mail.doctype.sieve_script.sieve_script.has_permission",
    "Vacation Response": "suite.mail.doctype.vacation_response.vacation_response.has_permission",
}

# ============================================================================
# Override standard doctype classes (drive)
# ============================================================================
override_doctype_class = {
    "File": "suite.drive.overrides.file.File",
}

# ============================================================================
# Override whitelisted methods (mail)
# ============================================================================
override_whitelisted_methods = {
    "frappe.core.doctype.user.user.update_password": "suite.mail.events.update_password",
    # Auth
    "mail.api.auth.validate": "suite.mail.api.auth.validate",
    # Outbound
    "mail.api.outbound.upload_attachment": "suite.mail.api.outbound.upload_attachment",
    "mail.api.outbound.send": "suite.mail.api.outbound.send",
    "mail.api.outbound.send_raw": "suite.mail.api.outbound.send_raw",
    # Inbound
    "mail.api.inbound.fetch_blob": "suite.mail.api.inbound.fetch_blob",
    "mail.api.inbound.pull": "suite.mail.api.inbound.pull",
    "mail.api.inbound.pull_raw": "suite.mail.api.inbound.pull_raw",
    # SpamD
    "mail.api.spamd.scan": "suite.mail.api.spamd.scan",
    "mail.api.spamd.get_spam_score": "suite.mail.api.spamd.get_spam_score",
    # writer — embed URLs baked into documents created by the standalone app
    "writer.api.embed.get": "suite.writer.api.embed.get",
}

# ============================================================================
# Document Events (deep-merged; per-doctype/per-event handler lists combined)
# ============================================================================
doc_events = {
    "File": {
        "on_update": "suite.meet.recording.ingest.delete_recording_metadata_for_removed_artifact",
    },
    "User Group": {
        "on_update": "suite.drive.utils.clear_user_group_cache",
        "on_trash": "suite.drive.utils.clear_user_group_cache",
    },
    "Presentation": {
        "on_update": ["suite.drive.overrides.file.sync_content_file"],
        "on_trash": ["suite.drive.overrides.file.sync_content_file"],
    },
    "Sheet": {
        # Same content-app wiring as Presentation: on_update mirrors title +
        # soft-trash onto the backing Drive File, on_trash removes it on hard
        # delete. Sheets routes its rename and trash/restore through doc.save so
        # these fire; the high-frequency cell-data autosave stays on db.set_value
        # (Drive doesn't track cell data) and deliberately fires nothing.
        "on_update": ["suite.drive.overrides.file.sync_content_file"],
        "on_trash": ["suite.drive.overrides.file.sync_content_file"],
    },
    "User": {
        # Roles are assigned before insert so they are present when Frappe's
        # User.validate runs — assigning them after insert triggers a spurious
        # "No Roles Specified" warning and leaves user_type mis-resolved.
        # //// Neoffice — we reached the same conclusion independently (e113aa921,
        # //// 31.08.2026): our own before_insert hooks replaced two after_insert
        # //// ones that reloaded and re-saved the just-inserted User. Combined with
        # //// the rest of this chain that meant several successive saves of the same
        # //// document, and public signup died on TimestampMismatchError — HTTP 417,
        # //// "Oups ! Quelque chose s'est mal passé." on screen, no account created.
        # //// Nobody could open an account on the shop. Upstream's assign_suite_role
        # //// now supersedes our assign_drive_role/assign_meet_role, but the rule
        # //// stands: nothing in this chain may save the User a second time.
        "before_insert": [
            "suite.utils.user.assign_suite_role",
        ],
        "after_insert": [
            "suite.drive.utils.users.create_drive_settings",
            "suite.mail.events.create_user_settings",
            # //// Neoffice — auto-provision the Stalwart mailbox (mail + calendar)
            # //// so both work out of the box on deploy. Upstream leaves mailbox
            # //// creation to an explicit admin action; our fleet ships instances
            # //// with mail already working, so it has to happen on user creation.
            # //// It must never write back to the User doc: every extra User.save
            # //// in this chain is what broke public signup with a
            # //// TimestampMismatchError (HTTP 417) on 31.08.2026.
            "suite.mail.events.provision_mail_account",
        ],
        "on_update": [
            "suite.mail.events.update_account_password",
            "suite.mail.events.clear_sessions_on_disable",
            "suite.mail.events.apply_disabled_account_role",
            "suite.mail.events.remove_disabled_account_role",
        ],
        "on_trash": [
            "suite.mail.events.delete_account",
            "suite.mail.events.delete_user_accounts",
            "suite.mail.events.delete_user_settings",
            # //// Neoffice — mirror of create_drive_settings above; upstream
            # //// provisions Drive Settings for every new user but never removes it.
            # //// The doctype autonames field:user, so the row's primary key IS the
            # //// e-mail: the row a deleted user leaves behind is picked up by the
            # //// NEXT account created with the same address, and get_user_folder()
            # //// then hands that account the previous owner's private folder.
            # //// Mail already cleans up after itself here; Drive did not.
            "suite.drive.utils.users.delete_drive_settings",
        ],
    },
}

user_invitation = {
    "allowed_roles": {
        "System Manager": ["Suite User"],
    },
}

# Suite's onboarding replaces the built-in desk setup wizard
setup_wizard_url = "/suite/setup"

# ============================================================================
# Scheduled Tasks (per-frequency lists combined; cron keys de-duplicated)
# ============================================================================
scheduler_events = {
    # //// Neoffice — added: shut coolwsd (Collabora Online) down after 15 minutes
    # //// with no editing session. Upstream ships no Office editing, so it has no
    # //// such daemon; ours idles at ~400 MB per instance and the fleet runs many
    # //// instances per host. See suite/drive/wopi/lifecycle.py.
    "all": [
        "suite.drive.wopi.lifecycle.stop_if_idle",
    ],
    "daily": [
        # meet
        "suite.meet.api.recording.cleanup_failed_recordings",
        # drive
        "suite.drive.api.scripts.auto_delete_from_trash",
        "suite.drive.api.scripts.clear_deleted_files",
        # sheets
        "suite.sheets.versioning.tasks.rollup_snapshots",
        "suite.sheets.versioning.tasks.truncate_op_log",
        "suite.sheets.trash.purge_trashed_sheets",
        # mail
        "suite.mail.doctype.jmap_account.jmap_account.delete_orphaned_jmap_accounts",
        "suite.mail.doctype.mail_exchange.mail_exchange.clean_import_export_directories",
        "suite.mail.doctype.push_subscription.push_subscription.renew_expiring_push_subscriptions",
        "suite.mail.doctype.contacts_exchange.contacts_exchange.clean_contacts_import_export_directories",
        "suite.calendar.doctype.calendar_exchange.calendar_exchange.clean_calendar_import_export_directories",
    ],
    "hourly": [
        # drive
        "suite.drive.api.scripts.clear_download_archives",
        "suite.drive.webdav.locks.purge_expired_locks",
        # mail
        "suite.mail.doctype.mail_exchange.mail_exchange.retry_stuck_mail_exchanges",
        "suite.calendar.doctype.calendar_exchange.calendar_exchange.retry_stuck_calendar_exchanges",
        "suite.mail.doctype.contacts_exchange.contacts_exchange.retry_stuck_contacts_exchanges",
    ],
    "cron": {
        "* * * * *": ["suite.meet.api.recording.reconcile_pending_recordings"],
        "*/5 * * * *": [
            # mail
            "suite.mail.doctype.server_job.server_job.retry_failed_jobs",
            "suite.mail.doctype.mail_queue.mail_queue.enqueue_process_pending_emails",
            "suite.mail.doctype.server_deployment.server_deployment.retry_failed_deployments",
            "suite.mail.doctype.server_ansible_play.server_ansible_play.retry_failed_ansible_plays",
        ],
    },
}

# ============================================================================
# Lifecycle hooks — dispatched through suite.suite_core.boot so that EACH
# former app's handler is preserved and invoked in order.
# ============================================================================
before_install = "suite.suite_core.boot.before_install"
after_install = "suite.suite_core.boot.after_install"
after_migrate = "suite.suite_core.boot.after_migrate"
after_app_install = "suite.suite_core.boot.after_app_install"
extend_bootinfo = "suite.suite_core.boot.extend_bootinfo"

# drive — custom upload + after_request middleware (single definers)
after_file_upload = "suite.drive.overrides.file.after_file_upload"
# //// Neoffice — Frappe v15 compatibility. Upstream writes response headers through
# //// `frappe.local.response_headers`, which v16 creates per request and merges into
# //// the response; v15 has neither half, so every write raised AttributeError and
# //// /suite and /drive answered HTTP 500 to every visitor. `create` makes the object
# //// (before_request) and `apply` merges it (after_request) — the same two points
# //// v16 uses. ORDER MATTERS: create must run before any handler writes a header,
# //// and apply last, once they all have. Drop both entries, and
# //// suite/suite_core/v15_response_headers.py, when the fleet moves to v16.
after_request = [
    "suite.drive.api.product.after_request",
    "suite.suite_core.v15_response_headers.apply",
]

# drive — WebDAV protocol dispatcher (list hook, additive; answers all verbs under /dav)
before_request = [
    # //// Neoffice — see the v15 note on after_request above; this one has to come
    # //// first, the WebDAV dispatcher below already writes a header.
    "suite.suite_core.v15_response_headers.create",
    "suite.drive.webdav.dispatch.handle_before_request",
]

# drive — the WebDAV dispatcher consumes /dav request bodies itself (frappe skips the
# body cap and form_dict buffering; a no-op on frappe versions without this hook,
# where PUT bodies fall back to buffered and capped)
streaming_request_paths = ["/dav/"]

# ============================================================================
# Fixtures (concatenated; identical entries de-duplicated)
# ============================================================================
fixtures = [
    # drive
    {"dt": "Custom Field", "filters": [["dt", "=", "File"]]},
    {"dt": "Property Setter", "filters": [["doc_type", "=", "File"]]},
    {"dt": "Role", "filters": [["role_name", "like", "Drive %"]]},
    # slides
    {"dt": "Presentation", "filters": [["is_template", "=", "1"]]},
    # meet
    {"dt": "Role", "filters": [["role_name", "like", "Meet %"]]},
    # mail / calendar
    {"dt": "Role", "filters": [["role_name", "like", "Suite %"]]},
]

# ============================================================================
# Misc carried-over hooks
# ============================================================================
# drive — custom signup template
signup_form_template = "templates/signup.html"

# mail — link integrity on delete
ignore_links_on_delete = [
    # drive — File.after_delete clears all of these itself, but the framework's
    # link check runs first and would refuse the delete before it gets the chance
    "Drive Settings",
    "Drive Permission",
    "Drive Favourite",
    "Drive Entity Log",
    "Drive Notification",
    "Drive Entity Activity Log",
    "Drive DAV Property",
    "Drive DAV Lock",
    # mail
    "Mail Account Request",
    "Server Job",
    "Server Ansible Play",
    "Server Deployment",
    "JMAP Account",
    "User Account",
    "Screened Email Address",
    "Mail Exchange",
    "Mail Queue",
    "Mail Signature",
    "Mail Sync History",
    "Mailbox Settings",
    "User Settings",
]

# mail — log retention (only definer; kept as dict)
default_log_clearing_doctypes = {"Mail Queue": 3, "Spam Check Log": 7}

export_python_type_annotations = True
require_type_annotated_api_methods = True

# ============================================================================
# Access-control path lists (concatenated; identical entries de-duplicated)
# ============================================================================
# drive
ALLOWED_PATHS = [
    "/api/method/create-site-migration",
    "/api/method/find-my-sites",
    "/api/method/frappe.realtime.get_user_info",
    "/api/method/frappe.realtime.can_subscribe_doc",
    "/api/method/frappe.realtime.can_subscribe_doctype",
    "/api/method/frappe.realtime.has_permission",
    "/api/method/frappe.www.login.login_via_frappe",
    "/api/method/frappe.integrations.oauth2.authorize",
    "/api/method/frappe.integrations.oauth2.approve",
    "/api/method/frappe.integrations.oauth2.get_token",
    "/api/method/frappe.integrations.oauth2.openid_profile",
    "/api/method/frappe.website.doctype.web_page_view.web_page_view.make_view_log",
    "/api/method/ping",
    "/api/method/login",
    "/api/method/logout",
    "/api/method/upload_file",
    "/api/method/frappe.search.web_search",
    "/api/method/frappe.email.queue.unsubscribe",
    "/api/method/frappe.website.doctype.web_form.web_form.accept",
    "/api/method/frappe.core.doctype.user.user.test_password_strength",
    "/api/method/frappe.core.doctype.user.user.update_password",
    # drive — WebDAV mount root
    "/dav",
]

ALLOWED_WILDCARD_PATHS = [
    "/api/method/frappe.integrations.oauth2_logins.",
    "/api/method/suite.mail.api.",
    # mail — backward-compatible prefix for the standalone `mail` app's
    # endpoints still called by Frappe Framework (see override_whitelisted_methods).
    "/api/method/mail.api.",
    "/api/method/suite.calendar.api.",
    "/api/method/suite.meet.api.",
    "/api/method/suite.drive.api.",
    "/api/method/suite.writer.api.",
    # writer — backward-compatible prefix for embed URLs stored in old documents
    # (see override_whitelisted_methods).
    "/api/method/writer.api.",
    "/api/method/suite.slides.api.",
    "/api/method/suite.sheets.api.",
    # drive — WebDAV namespace
    "/dav/",
]

DENIED_PATHS = []

DENIED_WILDCARD_PATHS = [
    "/api/",
]
