# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import base64
import json
import random
import string
import uuid

import frappe
from frappe.core.doctype.file.file import get_local_image
from frappe.model.document import Document
from frappe.utils.caching import redis_cache

SYSTEM_TEMPLATE_TITLES = {"Light", "Dark"}


class Presentation(Document):
	def before_save(self):
		self.slug = slug(self.title)
		if self.is_composite:
			self.is_public = 1

	def validate(self):
		if self.is_composite:
			if not self.reference_presentations:
				frappe.throw(
					"Please add at least one reference presentation to create a composite presentation."
				)

			for ref in self.reference_presentations:
				ref_doc = frappe.get_cached_doc("Presentation", ref.presentation)
				is_public = ref_doc.is_public
				ref_name = ref_doc.title
				if not is_public:
					frappe.throw(
						f"Reference presentation '{ref_name}' must be public to create a composite presentation."
					)


@frappe.whitelist()
def save_base64_image(base64_data: str, presentation_name: str, prefix: str) -> str:
	header, b64 = base64_data.split(",", 1)
	ext = header.split("/")[1].split(";")[0]
	filename = f"{prefix}-{uuid.uuid4().hex[:6]}.{ext}"

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


# whitelist needed for drive integration
@frappe.whitelist()
def get_presentation_thumbnail(presentation_name: str, index: int | None = 1) -> str:
	"""Returns the thumbnail of a presentation."""
	return frappe.get_value("Presentation", presentation_name, "thumbnail") or ""


@frappe.whitelist()
def get_presentations() -> list[dict]:
	"""
	Returns a list of presentation details
	- info and presentation thumbnail
	"""
	presentations = frappe.get_list(
		"Presentation",
		fields=["name", "title", "owner", "creation", "modified_by", "modified", "thumbnail"],
		order_by="modified desc",
		filters=[["owner", "=", frappe.session.user], ["is_template", "=", 0]],
	)

	for presentation in presentations:
		presentation["slide_count"] = frappe.db.count("Slide", {"parent": presentation["name"]})

	return presentations


@frappe.whitelist()
def update_slide_attachments(parent, slide):
	slide = json.loads(slide) if isinstance(slide, str) else slide

	elements_data = slide.get("elements") or "[]"
	elements = elements_data if isinstance(elements_data, list) else json.loads(elements_data)
	for element in elements:
		element["id"] = "".join(random.choices(string.ascii_lowercase + string.digits, k=9))
		if element.get("src") and element["src"].startswith("/private"):
			element["attachmentName"] = get_attachment(parent, element["src"])

	slide["elements"] = json.dumps(elements)

	return slide


def apply_slide_layout(slide, ref_id, parent):
	layout_slide = frappe.get_doc("Slide", ref_id)

	slide_dict = layout_slide.as_dict()
	slide_dict = update_slide_attachments(parent, slide_dict)

	for key, value in slide_dict.items():
		setattr(slide, key, value)


def create_new_slide(parent, ref_id):
	"""
	Creates a new slide with the given reference slide id.
	"""
	slide = frappe.new_doc("Slide")

	apply_slide_layout(slide, ref_id, parent)

	slide.parent = parent
	slide.parentfield = "slides"
	slide.parenttype = "Presentation"
	slide.save()

	return slide


def get_slides_from_ref(parent, theme, duplicate_from):
	ref_name = duplicate_from or theme or "Light"
	ref_presentation = frappe.get_doc("Presentation", ref_name)

	slides = []

	if duplicate_from:
		for slide in ref_presentation.slides:
			new_slide = create_new_slide(parent, slide.name)
			new_slide.idx = slide.idx
			slides.append(new_slide)
	else:
		first_index = 2 if ref_presentation.title in ("Light", "Dark") else 0
		first_slide = create_new_slide(parent, ref_presentation.slides[first_index].name)
		first_slide.idx = 1
		slides.append(first_slide)

	return slides


def is_system_template(template_title: str) -> bool:
	return template_title in SYSTEM_TEMPLATE_TITLES


def get_template_thumbnail(template_title: str, index: int) -> str:
	template_title = (template_title or "light").lower()
	return f"/assets/slides/frontend/images/layouts/{template_title}/thumbnail-{index}.webp"


def get_template_cover_thumbnail(template):
	template_title, template_thumbnail = frappe.get_value(
		"Presentation",
		template,
		["title", "thumbnail"],
	)
	return (
		get_template_thumbnail(template_title, 3)
		if is_system_template(template_title)
		else template_thumbnail
	)


def set_duplicate_metadata(presentation, duplicate_from):
	src_title, src_theme, src_thumbnail = frappe.get_value(
		"Presentation",
		duplicate_from,
		["title", "theme", "thumbnail"],
	)
	presentation.title = f"Copy of {src_title}"
	presentation.theme = src_theme
	presentation.thumbnail = src_thumbnail


def set_template_metadata(presentation, template):
	presentation.title = "Untitled"
	presentation.theme = template
	presentation.thumbnail = get_template_cover_thumbnail(template)


@frappe.whitelist()
def create_presentation(template=None, duplicate_from=None):
	presentation = frappe.new_doc("Presentation")
	if duplicate_from:
		set_duplicate_metadata(presentation, duplicate_from)
	else:
		set_template_metadata(presentation, template)
	presentation.insert()

	presentation.slides = get_slides_from_ref(presentation.name, template, duplicate_from)

	presentation.save()
	return presentation


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


def get_permission_query_conditions(user):
	if user == "Administrator":
		return ""

	if frappe.has_permission("Presentation", "read", user=user):
		return f"`tabPresentation`.owner = '{user}' OR `tabPresentation`.is_template = 1"


def has_permission(doc, ptype="read", user=None):
	if user == "Administrator":
		return True

	return doc.owner == user or (doc.is_template and ptype == "read")


@frappe.whitelist(allow_guest=True)
def is_public_presentation(name):
	return frappe.db.get_value("Presentation", name, "is_public") == 1


@frappe.whitelist(allow_guest=True)
def is_composite_presentation(name):
	return frappe.db.get_value("Presentation", name, "is_composite") == 1


@frappe.whitelist(allow_guest=True)
def get_public_presentation(name):
	if not is_public_presentation(name):
		frappe.throw("Presentation is not public", frappe.PermissionError)

	return frappe.get_doc("Presentation", name).as_dict()


def set_layouts_in_template(template):
	if template.get("is_template") is not None and not template.get("is_template"):
		return

	doc = frappe.get_doc("Presentation", template["name"])
	template["layouts"] = [slide.as_dict() for slide in doc.slides]
	title = doc.title

	for layout in template["layouts"]:
		if is_system_template(title):
			layout["thumbnail"] = get_template_thumbnail(title, layout["idx"])
		else:
			layout["thumbnail"] = ""


@frappe.whitelist()
@redis_cache()
def get_templates():
	templates = frappe.get_all(
		"Presentation",
		filters={"is_template": 1},
		fields=["name", "title", "slug", "creation", "is_template"],
		order_by="creation",
	)

	for template in templates:
		set_layouts_in_template(template)

	return templates


@frappe.whitelist(allow_guest=True)
def get_composite_presentation(name):
	doc = frappe.get_doc("Presentation", name)

	composite_slides = []

	for reference in doc.reference_presentations:
		ref_doc = frappe.get_cached_doc("Presentation", reference.presentation)
		for slide in ref_doc.slides:
			composite_slides.append(slide)

	doc.slides = composite_slides

	return doc.as_dict()


def can_convert_image(extn):
	return extn.lower() in ["png", "jpeg", "jpg"]


def convert_and_save_image(image, path):
	image.save(path, "WEBP")
	return path


def create_new_webp_file_doc(presentation_name, file_url, image, extn):
	files = frappe.get_all(
		"File",
		filters={
			"attached_to_name": presentation_name,
			"file_url": file_url,
		},
		fields=["name"],
		limit=1,
	)
	if files:
		_file = frappe.get_doc("File", files[0].name)
		webp_path = _file.get_full_path().replace(extn, "webp")
		convert_and_save_image(image, webp_path)
		new_file = frappe.copy_doc(_file)
		new_file.file_name = f"{_file.file_name.replace(extn, 'webp')}"
		new_file.file_url = f"{_file.file_url.replace(extn, 'webp')}"
		new_file.save()
		_file.delete()
		return new_file
	return file_url


@frappe.whitelist()
def get_webp_doc(presentation_name, file_doc):
	file_url = file_doc.get("file_url", "")
	if file_url.endswith((".webp", ".svg")):
		return file_doc

	image, filename, extn = get_local_image(file_url)

	if can_convert_image(extn):
		return create_new_webp_file_doc(presentation_name, file_url, image, extn)


def update_element_urls(presentation, element):
	attribute = "poster" if element.get("type") == "video" else "src"
	image_url = element.get(attribute, "")

	webp_doc = get_webp_doc(presentation, image_url)

	if webp_doc.file_url:
		element["attachmentName"] = webp_doc.name
		element[attribute] = webp_doc.file_url


@frappe.whitelist()
def optimize_images(name):
	doc = frappe.get_doc("Presentation", name)

	for slide in doc.slides:
		elements = json.loads(slide.elements or "[]")

		for element in elements:
			if element.get("type") in ["image", "video"]:
				update_element_urls(doc.name, element)

		slide.elements = json.dumps(elements, indent=2)

	return doc.save()


@frappe.whitelist(allow_guest=True)
def get_editor_access(presentation_id: str) -> str:
	is_composite = frappe.db.get_value("Presentation", presentation_id, "is_composite")
	if is_composite:
		return "view"

	has_access = frappe.has_permission("Presentation", "write", presentation_id)
	if has_access:
		return "edit"
	else:
		is_public = frappe.db.get_value("Presentation", presentation_id, "is_public")
		if is_public:
			return "view"

	return "none"
