# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe import _  # //// Neoffice — share e-mail and notification translated (#363).
from frappe.model.document import Document
from pypika import Order


def get_link(entity):
    if entity.file_type == "Document":
        return "/writer/w/" + entity.name
    type_ = {True: "f", bool(entity.is_folder): "d"}
    return entity.file_url if entity.file_type == "Link" else f"/drive/{type_.get(True)}/{entity.name}/"


@frappe.whitelist()
def get_notifications(only_unread: bool = False):
    User = frappe.qb.DocType("User")
    Notification = frappe.qb.DocType("Drive Notification")
    fields = [
        Notification.name,
        Notification.to_user,
        Notification.from_user,
        Notification.read,
        Notification.type,
        Notification.message,
        Notification.entity_type,
        Notification.notif_doctype,
        Notification.notif_doctype_name,
        Notification.creation,
        User.user_image,
        User.full_name,
    ]
    query = (
        frappe.qb.from_(Notification)
        .left_join(User)
        .on(Notification.from_user == User.name)
        .select(*fields)
        .orderby(Notification.creation, order=Order.desc)
    )

    if only_unread:
        query = query.where(Notification.read == 0)
    query = query.where(Notification.to_user == frappe.session.user)
    result = query.run(as_dict=True)
    return result


@frappe.whitelist()
def get_unread_count():
    """
    Return a count of records where user is current user and read is False
    """
    return frappe.db.count("Drive Notification", filters={"to_user": frappe.session.user, "read": 0})


@frappe.whitelist()
def mark_as_read(name: str | None = None, all: bool = False):
    if all:
        frappe.db.set_value(
            "Drive Notification", {"to_user": frappe.session.user, "read": False}, "read", True
        )
        return
    # filter on the recipient too: a bare name would let any caller flip the flag
    # on someone else's notification
    frappe.db.set_value("Drive Notification", {"name": name, "to_user": frappe.session.user}, "read", True)
    return


def notify_mentions(entity_name, mentions, comment=False):
    """
    Create a mention notification for each user mentioned
    :param entity_name: ID of entity
    :param document_name: ID of document containing mentions
    """
    entity = frappe.get_doc("File", entity_name)
    for mention in mentions:
        create_notification(
            frappe.session.user,
            mention,
            "Mention",
            entity,
            f"You were mentioned in a {'comment in:' if comment else 'document:'} {entity.file_name}",
        )


def notify_share(entity_name, docperm_name):
    """
    Create a share notification for each user
    :param entity_name: ID of entity
    :param document_name: ID of docshare containing share info
    """
    entity = frappe.get_doc("File", entity_name)
    docshare = frappe.get_doc("Drive Permission", docperm_name)

    # //// Neoffice — translated, one sentence per kind so the French agrees, and a name even
    # //// when the grant came from a session without one: upstream built an English f-string
    # //// that could read « None shared … » (#363). Everything below runs in the RECIPIENT's
    # //// language: this is a background job, whose frappe.local.lang is not theirs — the
    # //// first test on osiris sent the translated e-mail in English.
    from frappe.translate import get_user_lang, print_language

    with print_language(get_user_lang(docshare.user)):
        author_full_name = frappe.db.get_value("User", {"name": docshare.owner}, ["full_name"]) or _("Someone")
        entity_type = "document" if entity.file_type == "Document" else "folder" if entity.is_folder else "file"
        link = get_link(entity)
        message = {
            "folder": _('{0} shared a folder with you: "{1}"'),
            "file": _('{0} shared a file with you: "{1}"'),
            "document": _('{0} shared a document with you: "{1}"'),
        }[entity_type].format(author_full_name, entity.file_name)
        if not frappe.db.exists("User", docshare.user):
            key = frappe.get_value("Drive User Invitation", {"email": docshare.user})
            link = frappe.utils.get_url(
                f"/api/method/suite.drive.api.product.accept_invite?key={key}&redirect={link}"
            )
        else:
            create_notification(docshare.owner, docshare.user, "Share", entity, message)
            # //// Neoffice — absolute: a mail client cannot open « /drive/d/<id>/ » (#363).
            link = frappe.utils.get_url(link)
        send_share_email(docshare.user, message, link, entity_type)


def create_notification(from_user: str, to_user: str, type: str, entity: str, message: str | None = None):
    from suite.drive.api.permissions import get_user_access_for_user

    user_access = get_user_access_for_user(entity.name, to_user)
    if user_access.get("read") == 0:
        return

    entity_type = "Document" if entity.file_type == "Document" else "Folder" if entity.is_folder else "File"
    details = {
        "from_user": from_user,
        "to_user": to_user,
        "type": type,
        "entity_type": entity_type,
        "notif_doctype": "File",
        "notif_doctype_name": entity.name,
        "message": message,
    }
    notif = frappe.db.exists("Drive Notification", details)
    if notif:
        return False
    try:
        frappe.get_doc({"doctype": "Drive Notification", **details}).insert()
        return True
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Frappe Drive Notification Error")
        return False


def drive_logo_inline_images():
    """The Drive wordmark logo in frappe.sendmail's `embed=` format (templates
    reference it as embed="drive-logo.png")."""

    try:
        with open(frappe.get_app_path("suite", "public", "drive", "images", "logo.png"), "rb") as f:
            return [{"filename": "drive-logo.png", "filecontent": f.read()}]
    except OSError:
        return []


def send_share_email(to, message, link, type_):
    # //// Neoffice — subject and button translated; upstream sent « Frappe Drive - Folder
    # //// Shared » and « Open folder » in English to every recipient (#363).
    subject = {
        "folder": _("A folder was shared with you"),
        "file": _("A file was shared with you"),
        "document": _("A document was shared with you"),
    }.get(type_) or _("A file was shared with you")
    button = {
        "folder": _("Open the folder"),
        "file": _("Open the file"),
        "document": _("Open the document"),
    }.get(type_) or _("Open the file")
    try:
        frappe.sendmail(
            recipients=to,
            subject=subject,  # //// Neoffice — translated above (#363).
            template="drive_share",
            args={
                "message": message,
                "type": type_,
                "link": link,
                "button": button,  # //// Neoffice — translated label for the template (#363).
            },
            inline_images=drive_logo_inline_images(),
        )
    except Exception:
        pass
