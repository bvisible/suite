# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
from contextlib import suppress

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import IfNull, Now

from mail.jmap import get_jmap_client
from mail.utils import generate_uuid_style_hash
from mail.utils.dt import parse_iso_datetime


class JMAPPushSubscription(Document):
	@staticmethod
	def verify_push_subscription(account: str, subscription_id: str, verification_code: str) -> None:
		"""Verifies a push subscription using the provided verification code."""

		if not account or not subscription_id or not verification_code:
			frappe.throw(_("Invalid parameters for push subscription verification."))

		subscription = frappe.get_doc("JMAP Push Subscription", account)

		if subscription.verified:
			frappe.throw(_("Subscription already verified."))
		elif subscription.subscription_id != subscription_id:
			frappe.throw(_("Invalid subscription ID."))

		client = get_jmap_client(account)
		response = client.push_subscription_set_verification_code(subscription_id, verification_code)

		kwargs = {"verification_response": json.dumps(response, indent=4)}
		if response[0][1].get("updated"):
			kwargs.update(
				{
					"status": "Active",
					"verified": 1,
					"verified_at": frappe.utils.now(),
				}
			)
		elif response[0][1].get("notUpdated"):
			kwargs["status"] = "Failed to Verify"

		subscription._db_set(notify_update=True, **kwargs)

	@staticmethod
	def get_push_subscriptions(account: str) -> list[dict]:
		"""Returns a list of push subscriptions for the given account."""

		client = get_jmap_client(account)

		try:
			return client.push_subscription_get()
		except Exception:
			frappe.log_error(
				title=_("Failed to get push subscriptions"),
				message=frappe.get_traceback(with_context=True),
			)
			frappe.throw(_("Failed to get push subscriptions."))

	@staticmethod
	def destroy_push_subscriptions(account: str, subscription_ids: list[str] | None = None) -> None:
		"""Destroys the push subscriptions for the given account."""

		client = get_jmap_client(account)

		try:
			if not subscription_ids:
				subscription_ids = []
				for subscription in client.push_subscription_get():
					subscription_ids.append(subscription["id"])

			client.push_subscription_set_destroy(subscription_ids)
		except Exception:
			frappe.log_error(
				title=_("Failed to destroy push subscription(s)"),
				message=frappe.get_traceback(with_context=True),
			)
			frappe.throw(_("Failed to destroy push subscription(s)."))

	@property
	def account_uuid_hash(self) -> str:
		"""Returns a UUID-style hash of the account name."""

		return generate_uuid_style_hash(self.account)

	def before_insert(self) -> None:
		self.set_endpoint()

	def after_insert(self) -> None:
		self._subscribe()

	def on_trash(self) -> None:
		if self.subscription_id:
			JMAPPushSubscription.destroy_push_subscriptions(self.account, [self.subscription_id])

	def set_endpoint(self) -> None:
		"""Sets the endpoint URL for the push subscription."""

		if not self.endpoint:
			self.endpoint = (
				f"{frappe.utils.get_url()}/api/method/mail.api.jmap.push_notification?account={self.account}"
			)

	def _subscribe(self) -> None:
		"""Subscribes to the JMAP push subscription."""

		kwargs = {
			"verified": 0,
			"verified_at": None,
			"expires_at": None,
			"subscription_id": None,
			"verification_response": None,
			"renew_response": None,
		}
		device_client_id = f"frappe-{frappe.local.site.replace('.', '-')}-{self.account}"
		types = self.notification_types.split("\n") if self.notification_types else None

		try:
			client = get_jmap_client(self.account)
			response = client.push_subscription_create(
				self.account_uuid_hash, device_client_id, self.endpoint, types
			)

			kwargs["subscription_response"] = json.dumps(response, indent=4)
			if response.get("created"):
				kwargs.update(
					{
						"status": "Pending Verification",
						"expires_at": parse_iso_datetime(
							response["created"][self.account_uuid_hash]["expires"]
						),
						"subscription_id": response["created"][self.account_uuid_hash]["id"],
					}
				)
			else:
				frappe.throw(_("Failed to subscribe to JMAP Push Subscription."))

			self._db_set(**kwargs)
		except Exception:
			frappe.log_error(
				title=_("Failed to subscribe to JMAP Push Subscription"),
				message=frappe.get_traceback(with_context=True),
			)
			kwargs["status"] = "Failed to Subscribe"
			self._db_set(**kwargs)

	@frappe.whitelist()
	def renew(self) -> None:
		"""Renews the JMAP push subscription."""

		if not self.verified or not self.subscription_id:
			frappe.throw(_("Cannot renew a non-verified subscription."))
		elif self.status not in ["Active", "Expired", "Failed to Renew"]:
			frappe.throw(_("Cannot renew a subscription that is not active or expired."))

		client = get_jmap_client(self.account)

		try:
			response = client.push_subscription_set_expires(self.subscription_id)

			kwargs = {"renew_response": json.dumps(response, indent=4)}
			if response[0][1].get("updated"):
				new_expires = parse_iso_datetime(response[1][1]["list"][0]["expires"])

				if new_expires == self.expires_at:
					kwargs["status"] = "Failed to Renew"
				else:
					kwargs.update(
						{
							"status": "Active",
							"expires_at": new_expires,
						}
					)
			elif response[0][1].get("notUpdated"):
				kwargs["status"] = "Failed to Renew"
			else:
				frappe.throw(_("Failed to renew JMAP Push Subscription."))

			self._db_set(**kwargs)
		except Exception:
			frappe.log_error(
				title=_("Failed to renew push subscription"),
				message=frappe.get_traceback(with_context=True),
			)
			frappe.throw(_("Failed to renew push subscription."))

	@frappe.whitelist()
	def resubscribe(self) -> None:
		"""Resubscribes to the JMAP push subscription."""

		if self.status not in [
			"Expired",
			"Failed to Verify",
			"Failed to Renew",
			"Failed to Subscribe",
			"Pending Verification",
		]:
			frappe.throw(_("Cannot resubscribe a subscription that is not expired or failed."))

		if self.subscription_id:
			JMAPPushSubscription.destroy_push_subscriptions(self.account, [self.subscription_id])

		self._subscribe()

	@frappe.whitelist()
	def destroy_all_subscriptions(self) -> None:
		"""Destroys all push subscriptions for the account."""

		JMAPPushSubscription.destroy_push_subscriptions(self.account)
		self._subscribe()

	def _db_set(
		self,
		update_modified: bool = True,
		commit: bool = False,
		notify_update: bool = False,
		**kwargs,
	) -> None:
		"""Updates the document with the given key-value pairs."""

		self.db_set(kwargs, update_modified=update_modified, commit=commit)

		if notify_update:
			self.notify_update()


def create_jmap_push_subscription(account: str) -> "JMAPPushSubscription":
	"""Creates a JMAP Push Subscription for the given account."""

	if frappe.db.exists("JMAP Push Subscription", account):
		return frappe.get_doc("JMAP Push Subscription", account)

	push_subscription = frappe.new_doc("JMAP Push Subscription")
	push_subscription.account = account
	push_subscription.insert(ignore_permissions=True)

	return push_subscription


def delete_jmap_push_subscription(account: str) -> None:
	"""Deletes the JMAP Push Subscription for the given account."""

	frappe.delete_doc("JMAP Push Subscription", account, ignore_permissions=True)


def renew_push_subscriptions() -> None:
	"""Renews push subscriptions that are about to expire within the next 2 days."""

	PS = frappe.qb.DocType("JMAP Push Subscription")
	subscriptions = (
		frappe.qb.from_(PS)
		.select(PS.name)
		.where(
			(PS.verified == 1)
			& (IfNull(PS.subscription_id, "") != "")
			& (PS.expires_at < (Now() + Interval(days=2)))
			& (PS.status.isin(["Active", "Expired", "Failed to Renew"]))
		)
	).run(pluck="name")

	if not subscriptions:
		return

	for subscription in subscriptions:
		with suppress(Exception):
			push_subscription = frappe.get_doc("JMAP Push Subscription", subscription)
			push_subscription.renew()
