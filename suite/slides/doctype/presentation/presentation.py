# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Presentation(Document):
	def before_save(self):
		self.slug = slug(self.title)


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


@frappe.whitelist()
def insert_slide(name, index):
	presentation = frappe.get_doc("Presentation", name)
	new_slide = frappe.new_doc("Slide")
	new_slide.parent = name
	new_slide.parentfield = "slides"
	new_slide.parenttype = "Presentation"
	new_slide.idx = index + 1
	new_slide.save()
	presentation.slides = presentation.slides[: index + 1] + [new_slide] + presentation.slides[index + 1 :]
	for i in range(index + 1, len(presentation.slides)):
		presentation.slides[i].idx += 1
	presentation.save()
	return presentation


@frappe.whitelist()
def delete_slide(name, index):
	presentation = frappe.get_doc("Presentation", name)
	presentation.slides = presentation.slides[:index] + presentation.slides[index + 1 :]
	for i in range(index, len(presentation.slides)):
		presentation.slides[i].idx -= 1
	presentation.save()
	return presentation


@frappe.whitelist()
def duplicate_slide(name, index):
	presentation = frappe.get_doc("Presentation", name)
	new_slide = frappe.new_doc("Slide")
	new_slide.update(presentation.slides[index].as_dict())
	new_slide.idx = index + 1
	new_slide.save()
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
