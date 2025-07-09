# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os
import shutil
import zipfile

import frappe
import pexpect
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_bench_path, now, time_diff_in_seconds
from uuid_utils import uuid7

from mail.utils import get_stalwart_cli_path
from mail.utils.cache import get_account_for_user
from mail.utils.user import is_account_owner, is_system_manager


class MailImportExportJob(Document):
	def autoname(self) -> None:
		self.name = str(uuid7())

	def before_submit(self) -> None:
		self.status = "Queued"
		self.queued_at = now()

	def on_submit(self) -> None:
		self.process()

	def before_cancel(self) -> None:
		self.status = "Cancelled"

	def process(self) -> None:
		"""Enqueue the import or export job based on the operation type."""

		if self.operation == "Import":
			job_id = f"{self.name}:import"
			frappe.enqueue_doc(
				self.doctype,
				self.name,
				"_import",
				queue="long",
				timeout=1800,
				job_id=job_id,
				deduplicate=True,
				enqueue_after_commit=True,
			)
		elif self.operation == "Export":
			job_id = f"{self.name}:export"
			frappe.enqueue_doc(
				self.doctype,
				self.name,
				"_export",
				queue="long",
				timeout=1800,
				job_id=job_id,
				deduplicate=True,
				enqueue_after_commit=True,
			)

	@frappe.whitelist()
	def retry(self) -> None:
		"""Retry the import or export job."""

		frappe.only_for("System Manager")

		if self.operation == "Emport":
			if files := frappe.db.get_all(
				"File",
				{
					"attached_to_doctype": self.doctype,
					"attached_to_name": self.name,
					"attached_to_field": "file",
				},
				pluck="name",
			):
				for file in files:
					frappe.delete_doc("File", file)

		self._db_set(status="Queued", queued_at=now(), notify=True)
		self.process()

	def _import(self) -> None:
		if self.operation != "Import":
			return

		self._mark_started()
		kwargs = {}
		self._mark_completed(**kwargs)

	def _export(self) -> None:
		if self.operation != "Export":
			return

		self._mark_started()

		cli_path = get_stalwart_cli_path()
		export_dir = get_bench_path() + f"/sites/{frappe.local.site}/exports/{self.name}"
		zip_path = get_bench_path() + f"/sites/{frappe.local.site}/private/files/{self.name}.zip"
		os.makedirs(export_dir, exist_ok=True)

		kwargs = {}
		try:
			host, _credentials = self._get_host_and_credentials()
			cmd = f"{cli_path} -u {host} export account {self.account} {export_dir}"
			child = pexpect.spawn(cmd, encoding="utf-8", timeout=1500)
			child.expect("Enter administrator credentials or press \\[ENTER\\] to use OAuth:")
			child.sendline(_credentials)
			child.expect(pexpect.EOF)
			child.wait()
			output = child.before.strip() if child.before else "No output received"

			if child.exitstatus != 0:
				raise Exception(output)

			with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
				for root, _dirs, files in os.walk(export_dir):
					for file in files:
						full_path = os.path.join(root, file)
						arcname = os.path.relpath(full_path, export_dir)
						zipf.write(full_path, arcname)

			file = frappe.new_doc("File")
			file.file_url = f"/private/files/{self.name}.zip"
			file.attached_to_doctype = self.doctype
			file.attached_to_name = self.name
			file.attached_to_field = "file"
			file.insert()

			kwargs.update({"status": "Completed", "output": output})
		except Exception as e:
			kwargs.update({"status": "Failed", "output": str(e)})

		shutil.rmtree(export_dir)
		self._mark_completed(**kwargs)

	def _mark_started(self) -> None:
		"""Marks the job as started and updates the started_at and started_after fields."""

		started_at = now()
		started_after = time_diff_in_seconds(started_at, self.queued_at)
		self._db_set(status="In Progress", started_at=started_at, started_after=started_after, notify=True)

	def _get_host_and_credentials(self) -> tuple[str, str]:
		"""Returns the host and credentials for the account's cluster."""

		tenant = frappe.db.get_value("Mail Account", self.account, "tenant")
		cluster = frappe.get_doc("Mail Cluster", frappe.db.get_value("Mail Tenant", tenant, "cluster"))

		return (
			cluster.base_url,
			f"{cluster.fallback_admin_user}:{cluster.get_password('fallback_admin_password')}",
		)

	def _mark_completed(self, **kwargs) -> None:
		"""Marks the job as completed and updates the completed_at and duration fields."""

		kwargs["completed_at"] = now()
		kwargs["duration"] = time_diff_in_seconds(kwargs["completed_at"], self.started_at)

		if kwargs["status"] == "Failed":
			kwargs["failed_count"] = self.failed_count + 1

		self._db_set(notify=True, **kwargs)

	def _db_set(
		self,
		update_modified: bool = True,
		commit: bool = False,
		notify: bool = False,
		**kwargs,
	) -> None:
		"""Updates the document with the given key-value pairs."""

		self.db_set(kwargs, update_modified=update_modified, notify=notify, commit=commit)


def get_permission_query_condition(user: str | None = None) -> str:
	user = user or frappe.session.user

	if is_system_manager(user):
		return ""

	if account := get_account_for_user(user):
		return f"(`tabMail Import Export Job`.account = '{account}')"
	else:
		return "1=0"


def has_permission(doc: Document, ptype: str, user: str | None = None) -> bool:
	if doc.doctype != "Mail Import Export Job":
		return False

	user = user or frappe.session.user
	user_is_system_manager = is_system_manager(user)
	user_is_account_owner = is_account_owner(doc.account, user)

	if user_is_system_manager or user_is_account_owner:
		return True

	return False
