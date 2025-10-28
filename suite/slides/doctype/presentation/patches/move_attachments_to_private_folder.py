import json
import os

import frappe
from frappe.utils import now_datetime


def check_file_usage(file_doc):
	presentation_name = file_doc.attached_to_name
	if not presentation_name:
		return False

	presentation = frappe.get_doc("Presentation", presentation_name)

	for slide in presentation.slides or []:
		if slide.thumbnail == file_doc.file_url:
			return True

		elements = slide.get("elements", [])
		if isinstance(elements, str):
			elements = json.loads(elements or "[]")
			for element in elements:
				if element.get("src") == file_doc.file_url or element.get("poster") == file_doc.file_url:
					return True

	return False


def execute():
	attachments = frappe.get_all("File", filters={"attached_to_doctype": "Presentation"}, pluck="name")

	for attachment in attachments:
		file_doc = frappe.get_doc("File", attachment)

		file_path = file_doc.get_full_path()
		if not os.path.exists(file_path):
			continue

		if not check_file_usage(file_doc):
			try:
				file_doc.delete()
			except Exception as e:
				print(f"Error deleting file {file_doc.name}: {e}")
			continue

		if file_doc.is_private:
			continue

		try:
			file_doc.is_private = 1
			file_doc.save()
		except Exception:
			msg = frappe.get_traceback()
			if "Already Exists" not in msg and "Duplicate" not in msg and "exists" not in msg:
				raise

			base_name = file_doc.file_name or (
				file_doc.file_url.rsplit("/", 1)[-1] if file_doc.file_url else "file"
			)
			base_name = os.path.splitext(base_name)[0]
			unique_suffix = now_datetime().strftime("%S%f")
			file_doc.file_name = base_name + "-" + unique_suffix

			file_doc.is_private = 1
			file_doc.reload()
			file_doc.save()
