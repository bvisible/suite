# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from uuid_utils import uuid7

from mail.jmap import get_jmap_client
from mail.utils.dt import parse_iso_datetime


class JMAPPushSubscription(Document):
	@staticmethod
	def verify_push_subscription(account: str, subscription_id: str, verification_code: str) -> None:
		"""Verifies a push subscription using the provided verification code."""

		if not account or not subscription_id or not verification_code:
			frappe.throw(_("Invalid parameters for push subscription verification."))

		subscription = frappe.db.get_value(
			"JMAP Push Subscription",
			{"account": account, "subscription_id": subscription_id, "verified": 0},
			"name",
		)

		if not subscription:
			frappe.log_error(
				title="JMAP Push Subscription Not Found",
				message=str(
					{
						"account": account,
						"subscription_id": subscription_id,
						"verification_code": verification_code,
					}
				),
			)
			frappe.throw(_("JMAP Push Subscription Not Found."))

		client = get_jmap_client(account)
		response = client.push_subscription_set_verification_code(subscription_id, verification_code)

		kwargs = {"verification_response": json.dumps(response, indent=4)}
		if response.get("updated"):
			kwargs["verified"] = 1
			kwargs["status"] = "Active"
		elif response.get("notUpdated"):
			kwargs["status"] = "Failed to Verify"

		frappe.db.set_value("JMAP Push Subscription", subscription, kwargs)

	@staticmethod
	def get_push_subscriptions(account: str) -> list[dict]:
		"""Returns a list of push subscriptions for the given account."""

		client = get_jmap_client(account)
		return client.push_subscription_get()

	@staticmethod
	def destroy_push_subscriptions(account: str, subscription_ids: list[str] | None = None) -> None:
		"""Destroys the push subscriptions for the given account."""

		client = get_jmap_client(account)

		if not subscription_ids:
			subscription_ids = []
			for subscription in client.push_subscription_get():
				subscription_ids.append(subscription["id"])

		client.push_subscription_set_destroy(subscription_ids)

	def autoname(self) -> None:
		self.name = str(uuid7())

	def before_insert(self) -> None:
		self.set_endpoint()

	def after_insert(self) -> None:
		self._subscribe()

	def set_endpoint(self) -> None:
		"""Sets the endpoint URL for the push subscription."""

		if not self.endpoint:
			self.endpoint = (
				f"{frappe.utils.get_url()}/api/method/mail.api.jmap.push_notification?account={self.account}"
			)

	def _subscribe(self) -> None:
		"""Subscribes to the JMAP push subscription."""

		device_client_id = f"frappe-{frappe.local.site.replace('.', '-')}-{self.account}"
		types = self.notification_types.split("\n") if self.notification_types else None
		client = get_jmap_client(self.account)
		response = client.push_subscription_create(self.name, device_client_id, self.endpoint, types)

		kwargs = {"subscription_response": json.dumps(response, indent=4)}
		if response.get("created"):
			kwargs["status"] = "Pending Verification"
			kwargs["subscription_id"] = response["created"][self.name]["id"]
			kwargs["expires_at"] = parse_iso_datetime(response["created"][self.name]["expires"])
		elif response.get("notCreated"):
			kwargs["status"] = "Failed to Subscribe"
		else:
			frappe.throw(_("Failed to subscribe to JMAP Push Subscription."))

		self._db_set(**kwargs)

	def _renew(self) -> None:
		"""Renews the JMAP push subscription."""

		if not self.verified or not self.subscription_id:
			frappe.throw(_("Cannot renew a non-verified subscription."))
		elif self.status not in ["Active", "Expired", "Failed to Renew"]:
			frappe.throw(_("Cannot renew a subscription that is not active or expired."))

		client = get_jmap_client(self.account)
		response = client.push_subscription_set_expires(self.subscription_id)

		kwargs = {"renew_response": json.dumps(response, indent=4)}
		if response.get("updated"):
			kwargs["expires_at"] = parse_iso_datetime(response["updated"][self.name]["expires"])
		elif response.get("notUpdated"):
			kwargs["status"] = "Failed to Renew"
		else:
			frappe.throw(_("Failed to renew JMAP Push Subscription."))

		self._db_set(**kwargs)

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
