# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os
import shlex
import shutil

import frappe
import pexpect
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_bench_path, now, time_diff_in_seconds
from uuid_utils import uuid7

from mail.utils import (
	compress_directory,
	extract_compressed_file,
	get_export_directory,
	get_import_directory,
	get_mbox_files,
	get_stalwart_cli_path,
)
from mail.utils.cache import get_account_for_user
from mail.utils.user import is_account_owner, is_system_manager
from mail.utils.validation import (
	validate_jmap_structure,
	validate_maildir_or_maildirpp,
	validate_nested_maildir_tree,
)


class MailImportExportJob(Document):
	def autoname(self) -> None:
		self.name = str(uuid7())

	def validate(self) -> None:
		if self.operation == "Import":
			self.validate_import_format()
			self.validate_import_file()
		elif self.operation == "Export":
			self.validate_export_format()

	def before_submit(self) -> None:
		self.status = "Queued"
		self.queued_at = now()

	def on_submit(self) -> None:
		self.process()

	def before_cancel(self) -> None:
		self.status = "Cancelled"

	def validate_import_format(self) -> None:
		"""Validate the import format."""

		if not self.import_format:
			frappe.throw(_("Import Format is required."))

	def validate_import_file(self) -> None:
		"""Validate the import file."""

		if not self.import_file:
			frappe.throw(_("Import File is required."))

		allowed_extensions = [".zip", ".tgz", ".tar.gz"]
		if not self.import_file.endswith(tuple(allowed_extensions)):
			frappe.throw(
				_("Only {0} files are supported for import.").format(
					", ".join(f"<code>{ext}</code>" for ext in allowed_extensions)
				)
			)

	def validate_export_format(self) -> None:
		"""Validate the export format."""

		if not self.export_format:
			frappe.throw(_("Export Format is required."))

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
		"""Imports the account data."""

		if self.operation != "Import":
			return

		self._mark_started()
		import_file = os.path.join(get_bench_path(), f"sites/{frappe.local.site}{self.import_file}")
		import_base = os.path.join(get_import_directory(), self.name)
		os.makedirs(import_base, exist_ok=True)

		kwargs = {}
		try:
			cli_path = get_stalwart_cli_path()
			extract_compressed_file(import_file, import_base)
			host, _credentials = self._get_host_and_credentials()

			command = [cli_path, "-u", host, "import"]
			if self.import_format == "jmap":
				command.append("account")
			else:
				command.extend(["messages", "-f", self.import_format])
			command.append(self.account)

			if self.import_format == "mbox":
				mbox_files = get_mbox_files(import_base)

				if len(mbox_files) == 0:
					frappe.throw(_("No {0} file found in the archive.").format("<code>.mbox</code>"))
				elif len(mbox_files) > 1:
					frappe.throw(
						_("Multiple {0} files found. Please provide only one.").format("<code>.mbox</code>")
					)

				command.append(mbox_files[0])
			elif self.import_format == "jmap":
				_import_base = os.path.join(import_base, self.account)
				validate_jmap_structure(_import_base, raise_exception=True)
				command.append(_import_base)
			else:
				if self.import_format == "maildir":
					validate_maildir_or_maildirpp(import_base, raise_exception=True)
				elif self.import_format == "maildir-nested":
					validate_nested_maildir_tree(import_base, raise_exception=True)

				command.append(import_base)

			output = _run_stalwart_cli_command(command, _credentials)
			kwargs.update({"status": "Completed", "output": output})
		except Exception as e:
			kwargs.update({"status": "Failed", "output": str(e)})

		shutil.rmtree(import_base, ignore_errors=True)
		self._mark_completed(**kwargs)

	def _export(self) -> None:
		"""Exports the account data."""

		if self.operation != "Export":
			return

		self._mark_started()
		export_base = os.path.join(get_export_directory(), self.name)
		export_file_name = f"{self.name}{self.export_format}"
		export_file_url = f"/private/files/{export_file_name}"
		export_file = os.path.join(get_bench_path(), f"sites/{frappe.local.site}{export_file_url}")
		os.makedirs(export_base, exist_ok=True)

		kwargs = {}
		try:
			cli_path = get_stalwart_cli_path()
			host, _credentials = self._get_host_and_credentials()
			command = f"{cli_path} -u {host} export account {self.account} {export_base}"
			output = _run_stalwart_cli_command(command, _credentials)

			compress_directory(export_base, export_file)
			file = frappe.new_doc("File")
			file.is_private = 1
			file.file_url = export_file_url
			file.file_name = export_file_name
			file.attached_to_doctype = self.doctype
			file.attached_to_name = self.name
			file.attached_to_field = "file"
			file.insert()

			# https://github.com/frappe/frappe/issues/26615
			frappe.db.set_value(
				"File", file.name, {"file_url": export_file_url, "file_name": export_file_name}
			)

			kwargs.update({"status": "Completed", "output": output})
		except Exception as e:
			kwargs.update({"status": "Failed", "output": str(e)})

		shutil.rmtree(export_base, ignore_errors=True)
		self._mark_completed(**kwargs)

	def _mark_started(self) -> None:
		"""Marks the job as started and updates the started_at and started_after fields."""

		started_at = now()
		started_after = time_diff_in_seconds(started_at, self.queued_at)
		self._db_set(
			status="In Progress", started_at=started_at, started_after=started_after, notify=True, commit=True
		)

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


def _run_stalwart_cli_command(command: str | list[str], _credentials: str, timeout: int = 1500) -> str:
	"""Runs the stalwart CLI command with the provided credentials and returns the output."""

	if isinstance(command, list):
		command = " ".join(shlex.quote(arg) for arg in command)

	child = pexpect.spawn(command, encoding="utf-8", timeout=timeout)
	child.expect("Enter administrator credentials or press \\[ENTER\\] to use OAuth:")
	child.sendline(_credentials)
	child.expect(pexpect.EOF)
	child.wait()
	output = child.before.strip() if child.before else "No output received."

	if child.exitstatus != 0:
		raise Exception(output)

	return output


def clean_import_export_directories() -> None:
	"""Called by the scheduler to clean up import and export directories."""

	for directory in (get_import_directory(), get_export_directory()):
		if os.path.exists(directory):
			for item in os.listdir(directory):
				item_path = os.path.join(directory, item)
				if os.path.isdir(item_path):
					if frappe.db.exists("Mail Import Export Job", {"name": item, "status": "In Progress"}):
						continue

					shutil.rmtree(item_path, ignore_errors=True)
				else:
					os.remove(item_path)
