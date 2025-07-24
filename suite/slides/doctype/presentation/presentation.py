# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import base64
import json
import random
import string
import uuid

import frappe
from frappe.model.document import Document


class Presentation(Document):
	def before_save(self):
		self.slug = slug(self.title)

	def update_thumbnails(self):
		old_slides = self.get_doc_before_save().slides

		for slide in self.slides:
			if slide.thumbnail and slide.thumbnail.startswith("data:image"):
				old_thumbnail = old_slides[slide.idx - 1].thumbnail
				delete_old_thumbnail(slide.name, old_thumbnail)
				slide.thumbnail = save_base64_thumbnail(slide.thumbnail, self.name)

	def validate(self):
		self.update_thumbnails()


def delete_old_thumbnail(slide_id: Document, old_thumbnail: str | None = None):
	if old_thumbnail and old_thumbnail.startswith("/private/files/"):
		if frappe.db.exists("Slide", {"thumbnail": old_thumbnail, "name": ["!=", slide_id]}):
			return
		try:
			file_doc = frappe.db.get_value("File", {"file_url": old_thumbnail})
			frappe.delete_doc("File", file_doc)
		except Exception as e:
			frappe.log_error(f"Failed to remove old thumbnail: {e}")


def save_base64_thumbnail(base64_data: str, presentation_name: str) -> str:
	header, b64 = base64_data.split(",", 1)
	ext = header.split("/")[1].split(";")[0]
	filename = f"thumbnail-{uuid.uuid4().hex[:6]}.{ext}"

	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": filename,
			"content": base64.b64decode(b64),
			"is_private": 1,
			"attached_to_doctype": "Presentation",
			"attached_to_name": presentation_name,
		}
	).insert()

	return file_doc.file_url


def slug(text: str) -> str:
	return text.lower().replace(" ", "-")


def get_presentation_thumbnail(presentation_name: str) -> str:
	"""Returns the thumbnail of the first slide in a presentation"""
	return frappe.get_value(
		"Slide",
		{"parent": presentation_name, "idx": 1},
		"thumbnail",
	)


@frappe.whitelist()
def get_all_presentations() -> list[dict]:
	"""
	Returns a list of presentation details
	- info and first thumbnail
	"""
	presentations = frappe.get_list(
		"Presentation",
		fields=["name", "title", "owner", "creation", "modified_by", "modified"],
		filters={"owner": frappe.session.user},
		order_by="modified desc",
	)

	for presentation in presentations:
		presentation["thumbnail"] = get_presentation_thumbnail(presentation["name"])

	return presentations


@frappe.whitelist()
def get_slide_thumbnails(presentation: str) -> list[str]:
	"""
	Returns a list of thumbnails for all slides in a presentation
	"""
	slides = frappe.get_all(
		"Slide",
		fields=["name", "thumbnail"],
		filters={"parent": presentation},
		order_by="idx",
	)

	return [slide["thumbnail"] for slide in slides]


@frappe.whitelist()
def get_presentation(name: str) -> Document:
	return frappe.get_doc("Presentation", name)


def create_new_slide(presentation, index, layout_id=None):
	"""
	Creates a new slide with the given layout_id.
	If no layout_id is provided, it creates a blank slide.
	"""
	new_slide = frappe.new_doc("Slide")
	new_slide.parent = presentation
	new_slide.parentfield = "slides"
	new_slide.parenttype = "Presentation"
	new_slide.idx = index + 1
	if layout_id:
		layout_slide = frappe.get_doc("Slide", layout_id)
		new_slide.update(layout_slide.as_dict())
		elements = json.loads(layout_slide.elements)
		for element in elements:
			element["id"] = "".join(random.choices(string.ascii_lowercase + string.digits, k=9))
		new_slide.elements = json.dumps(elements)
	new_slide.save()

	return new_slide


@frappe.whitelist()
def insert_slide(name, index, layout_id=None):
	presentation = frappe.get_doc("Presentation", name)
	new_slide = create_new_slide(name, index, layout_id)
	presentation.slides = presentation.slides[: index + 1] + [new_slide] + presentation.slides[index + 1 :]
	for i in range(index + 1, len(presentation.slides)):
		presentation.slides[i].idx += 1
	presentation.save()
	return presentation


@frappe.whitelist()
def delete_slide(name, index):
	presentation = frappe.get_doc("Presentation", name)
	slide = presentation.slides[index]
	delete_old_thumbnail(slide.name, slide.thumbnail)
	presentation.slides = presentation.slides[:index] + presentation.slides[index + 1 :]
	for i in range(index, len(presentation.slides)):
		presentation.slides[i].idx -= 1
	presentation.save()
	return presentation


def add_duplicate_slide(old_slide, idx):
	new_slide = frappe.new_doc("Slide")
	new_slide.update(old_slide.as_dict())
	elements = json.loads(old_slide.elements)
	for element in elements:
		element["id"] = "".join(random.choices(string.ascii_lowercase + string.digits, k=9))
	new_slide.elements = json.dumps(elements)
	new_slide.idx = idx
	return new_slide.save()


@frappe.whitelist()
def duplicate_slide(name, index):
	presentation = frappe.get_doc("Presentation", name)
	new_slide = add_duplicate_slide(presentation.slides[index], index + 1)
	presentation.slides = presentation.slides[: index + 1] + [new_slide] + presentation.slides[index + 1 :]
	for i in range(index + 1, len(presentation.slides)):
		presentation.slides[i].idx += 1
	presentation.save()
	return presentation


@frappe.whitelist()
def create_presentation(title, duplicate_from=None):
	new_presentation = frappe.new_doc("Presentation")
	new_presentation.title = title
	if duplicate_from:
		presentation = frappe.get_doc("Presentation", duplicate_from)
		new_presentation.name = None
		new_presentation.slides = presentation.slides
	else:
		slide = frappe.new_doc("Slide")
		slide.elements = "[]"
		new_presentation.slides = [slide]
	new_presentation.save()
	return new_presentation


@frappe.whitelist()
def delete_presentation(name):
	return frappe.delete_doc("Presentation", name)


@frappe.whitelist()
def update_title(name, title):
	frappe.set_value("Presentation", name, "title", title)
	return slug(title)


def get_attachment(presentation, file_url):
	"""
	Returns the attachment name for a file URL in a presentation.
	"""
	# if file is already attached to the presentation, return its name
	attachment = frappe.get_value("File", {"file_url": file_url, "attached_to_name": presentation}, "name")

	# if not, create a File doc from the source presentation's attachment from where this element was copied
	if not attachment:
		source_doc = frappe.get_all("File", filters={"file_url": file_url}, limit=1)
		if source_doc:
			new_attachment_doc = frappe.copy_doc(frappe.get_doc("File", source_doc[0].name))
			new_attachment_doc.attached_to_name = presentation
			new_attachment_doc.insert()
			attachment = new_attachment_doc.name

	return attachment


@frappe.whitelist()
def get_updated_json(presentation, json):
	for element in json:
		if element.get("type") in ["image", "video"]:
			file_url = element.get("src").replace(frappe.local.site_name, "")
			name = get_attachment(presentation, file_url)
			element["attachmentName"] = name

	return json


@frappe.whitelist()
def get_layouts():
	layout_presentation = frappe.get_doc("Slide Layouts")
	return layout_presentation.slides
