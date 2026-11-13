# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations

# //// Neoffice — urlencode and _ serve accept() (neoffice-maintenance#2296); hashlib and hmac, get_invite_token
import hashlib
import hmac
from urllib.parse import urlencode

import frappe
from frappe import _  # //// Neoffice — see accept()
from frappe.model.document import Document
from frappe.utils import add_days, get_datetime, now, validate_email_address

from suite.suite_core import suite_email

EXPIRY_DAYS = 1


class DriveUserInvitation(Document):
    def has_expired(self):
        return get_datetime(self.creation) < get_datetime(add_days(now(), -EXPIRY_DAYS))

    def before_insert(self):
        validate_email_address(self.email, True)

    def after_insert(self):
        if self.status == "Pending":
            try:
                self.invite_via_email()
            except BaseException as e:
                frappe.log_error(f"Failed to send invite email: {e}")
                pass
        elif self.status == "Proposed":
            admins = frappe.get_all(
                "Has Role", filters={"role": "Suite Admin", "parenttype": "User"}, pluck="parent"
            )
            for admin in admins:
                frappe.get_doc(
                    {
                        "doctype": "Drive Notification",
                        "to_user": admin,
                        "type": "Site",
                        "message": f"A person ({self.email}) from your domain has joined Frappe Drive",
                    }
                ).insert(ignore_permissions=True)
            frappe.db.commit()

    def invite_via_email(self):
        from suite.drive.api.notifications import drive_logo_inline_images

        # //// Neoffice — the link carries the key: it is built on the site's configured address, never on the
        # //// Host header of the request that made the invitation (neoffice-maintenance#2296).
        # //// Neoffice — and its token (get_invite_token, GHSA-xqwr-x9c5-vvf8)
        link = get_invite_link(self.name)
        suite_email.send(
            "drive-invite",
            self.email,
            {"inviter": frappe.utils.get_fullname(frappe.session.user), "link": link},
            local={
                "subject": "Frappe Drive - Invitation",
                "template": "drive_invitation",
                "args": {"invite_link": link, "user": frappe.session.user},
                "inline_images": drive_logo_inline_images(),
            },
        )

    # //// Neoffice — `token`: see get_invite_token (GHSA-xqwr-x9c5-vvf8)
    def accept(self, redirect=True, token=None):
        if self.status not in ["Pending", "Automatic"]:
            frappe.throw("This key has already been used")
        if self.status == "Expired" or self.has_expired():
            self.status = "Expired"
            self.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.throw("Invalid or expired key")

        exists = frappe.db.exists(
            "Account Request",
            {
                "email": self.email,
                "signed_up": 1,
            },
        )

        # //// Neoffice — the sign-up request is made only for an address that has no account yet: an existing
        # //// account signs in below instead (neoffice-maintenance#2296). And only from the e-mailed link: the key alone
        # //// made a verified request for whoever held it (get_invite_token, GHSA-xqwr-x9c5-vvf8).
        signs_up = not exists and not frappe.db.exists("User", self.email)
        if signs_up and not (
            isinstance(token, str) and hmac.compare_digest(token, get_invite_token(self.name))
        ):
            frappe.throw(
                _("Please open the link of your invitation e-mail to sign up, or ask for a new invitation."),
                frappe.PermissionError,
            )

        if redirect:
            frappe.local.response["type"] = "redirect"

        # //// Neoffice — see `signs_up` above
        if signs_up:
            # If the user does not have an account, redirect to sign up
            req = frappe.get_doc(
                {
                    "doctype": "Account Request",
                    "email": self.email,
                    "invite": self.name,
                    "login_count": 1,
                }
            ).insert(ignore_permissions=True)
            frappe.db.commit()

            # //// Neoffice — the values are encoded, and the redirect is a path of this site (accept_invite)
            query = {"e": self.email, "r": req.name}
            if isinstance(redirect, str):
                query["redirect-to"] = redirect
            url = "/drive/signup?" + urlencode(query)
            frappe.local.response["location"] = url
            return

        # //// Neoffice — upstream signed a visitor in as the invited account with login_as: no password, no second
        # //// factor, for whoever held the key (a Drive admin can read every key). The invited person now signs in
        # //// with their own credentials, then comes back to this link, and only they can accept it
        # //// (neoffice-maintenance#2296).
        if frappe.session.user == "Guest":
            back = f"/api/method/suite.drive.api.product.accept_invite?key={self.name}"
            url = "/login?" + urlencode({"redirect-to": back})
            frappe.local.response["location"] = url
            return url
        if not self.is_for(frappe.session.user):
            frappe.throw(_("This invitation was sent to another account."), frappe.PermissionError)

        self.status = "Accepted"
        self.accepted_at = frappe.utils.now()
        self.save(ignore_permissions=True)
        frappe.db.commit()

        # //// Neoffice — upstream's login_as stood here; the sign-in now happens before, see above
        frappe.local.response["location"] = "/drive/"
        return "/drive/"

    # //// Neoffice — added (neoffice-maintenance#2296): whether `user` is the person this invitation was sent to
    def is_for(self, user: str | None) -> bool:
        if not user or user == "Guest" or not self.email:
            return False
        email = frappe.db.get_value("User", user, "email") or user
        return email.strip().lower() == self.email.strip().lower()


# //// Neoffice — added (GHSA-xqwr-x9c5-vvf8 of frappe/drive, fixed there in 0.4.2): the key of an invitation does not
# //// prove that one received it. Suite Admin reads every invitation, and a link passes from hand to hand: for an
# //// address with no account, the key alone made a verified sign-up request (login_count 1), and whoever held it
# //// created the account of that address with a password of their choosing. The e-mailed link carries an HMAC of the
# //// key under the site's encryption key, which only the e-mail has. Same token as upstream's.
def get_invite_token(key: str) -> str:
    """The proof, carried by the e-mailed link only, that its holder received the invitation."""
    from frappe.utils.password import get_encryption_key

    message = f"Drive User Invitation {key}".encode()
    return hmac.new(get_encryption_key().encode(), message, hashlib.sha256).hexdigest()


# //// Neoffice — added, see get_invite_token: the link of the invitation e-mail and of a share's e-mail to an address
# //// with no account, on the site's configured address, never the Host header of the request (#2296)
def get_invite_link(key: str, redirect: str | None = None) -> str:
    query = {"key": key, "token": get_invite_token(key)}
    if redirect:
        query["redirect"] = redirect
    return frappe.utils.get_url(
        "/api/method/suite.drive.api.product.accept_invite?" + urlencode(query), allow_header_override=False
    )
