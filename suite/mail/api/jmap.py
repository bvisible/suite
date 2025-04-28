import frappe
from frappe import _

from mail.mail.doctype.email_message.email_message import enqueue_fetch_changes
from mail.mail.doctype.jmap_push_subscription.jmap_push_subscription import JMAPPushSubscription


@frappe.whitelist(methods=["POST"], allow_guest=True)
def push_notification(account: str) -> dict:
	"""Handle JMAP Push Notification."""

	try:
		data = frappe.request.get_json()

		if data["@type"] == "PushVerification":
			JMAPPushSubscription.verify_push_subscription(
				account, data["pushSubscriptionId"], data["verificationCode"]
			)
			return {}
		elif data["@type"] == "StateChange":
			enqueue_fetch_changes(account)
			return {}
		else:
			frappe.throw(_("Invalid Push Notification @type = {0}").format(data["@type"]))
	except Exception:
		frappe.log_error(
			title=_("Failed to handle JMAP Push Notification"),
			message=frappe.get_traceback(with_context=True),
		)
		return {"status": "error", "message": _("Failed to handle JMAP Push Notification.")}
