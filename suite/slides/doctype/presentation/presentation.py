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


class Presentation(Document):
	def before_save(self):
		self.slug = slug(self.title)
		if self.is_composite:
			self.is_public = 1

	def update_thumbnails(self):
		doc_before_save = self.get_doc_before_save()
		if not doc_before_save or not doc_before_save.slides:
			return
		old_slides = doc_before_save.slides

		for slide in self.slides:
			old_slide = old_slides[slide.idx - 1] if slide.idx <= len(old_slides) else None
			if not old_slide:
				continue
			if slide.thumbnail and slide.thumbnail.startswith("data:image"):
				old_thumbnail = old_slide.thumbnail
				delete_old_thumbnail(old_thumbnail)
				slide.thumbnail = save_base64_thumbnail(slide.thumbnail, self.name, "thumbnail")

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

		self.update_thumbnails()


def delete_old_thumbnail(old_thumbnail: str | None = None):
	if old_thumbnail and old_thumbnail.startswith("/files"):
		try:
			url = "/private" + old_thumbnail
			file_docname = frappe.db.get_value("File", {"file_url": url})
			frappe.delete_doc("File", file_docname)
		except Exception as e:
			frappe.log_error(f"Failed to remove old thumbnail: {e}")


@frappe.whitelist()
def save_base64_thumbnail(base64_data: str, presentation_name: str, prefix: str) -> str:
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


def get_presentation_thumbnail(presentation_name: str, index: int | None = 1) -> str:
	"""Returns the thumbnail of the first slide in a presentation"""
	return frappe.get_value(
		"Slide",
		{"parent": presentation_name, "idx": index},
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
		fields=["name", "title", "owner", "creation", "modified_by", "modified", "is_public"],
		filters={"owner": frappe.session.user, "is_template": 0},
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


def apply_slide_layout(slide, ref_id):
	layout_slide = frappe.get_doc("Slide", ref_id)

	slide.update(layout_slide.as_dict())

	elements = json.loads(layout_slide.elements)
	for element in elements:
		element["id"] = "".join(random.choices(string.ascii_lowercase + string.digits, k=9))

	slide.elements = json.dumps(elements)


def create_new_slide(parent, ref_id, copy_thumbnail=False):
	"""
	Creates a new slide with the given reference slide id.
	"""
	slide = frappe.new_doc("Slide")

	apply_slide_layout(slide, ref_id)

	if not copy_thumbnail:
		slide.thumbnail = ""

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
			new_slide = create_new_slide(parent, slide.name, True)
			new_slide.idx = slide.idx
			slides.append(new_slide)
	else:
		first_index = 2 if ref_presentation.title in ("Light", "Dark") else 0
		first_slide = create_new_slide(parent, ref_presentation.slides[first_index].name)
		first_slide.idx = 1
		slides.append(first_slide)

	return slides


@frappe.whitelist()
def create_presentation(title, theme=None, duplicate_from=None):
	presentation = frappe.new_doc("Presentation")
	presentation.title = title
	presentation.theme = theme
	presentation.insert()

	presentation.slides = get_slides_from_ref(presentation.name, theme, duplicate_from)

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


@frappe.whitelist()
def get_layouts(theme):
	layout_doc = frappe.get_doc("Presentation", theme) if frappe.db.exists("Presentation", theme) else None
	slides = []
	if layout_doc and layout_doc.is_template and "Slides User" in frappe.get_roles():
		slides = layout_doc.slides

	return {
		"slides": slides,
		"is_public": layout_doc.is_public if layout_doc else 0,
	}


def get_permission_query_conditions(user):
	if user == "Administrator":
		return ""

	if frappe.has_permission("Presentation", "read", user=user):
		return f"`tabPresentation`.owner = '{user}' OR `tabPresentation`.is_template = 1"


def has_permission(doc, ptype="read", user=None):
	if user == "Administrator":
		return True

	user_roles = set(frappe.get_roles(user))

	if "Slides User" in user_roles:
		return doc.owner == user or (doc.is_template and ptype == "read")

	return False


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


@frappe.whitelist()
def get_themes():
	themes = frappe.get_all(
		"Presentation",
		filters={"is_template": 1},
		fields=["name", "title", "slug", "is_public"],
		order_by="title",
	)

	for theme in themes:
		if theme["title"] in ("Light", "Dark"):
			theme["thumbnail"] = get_presentation_thumbnail(theme["name"], 3)
		else:
			theme["thumbnail"] = get_presentation_thumbnail(theme["name"])

	return themes


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


def create_new_webp_file_doc(presentation, file_url, image, extn):
	files = frappe.get_all(
		"File",
		filters={
			"attached_to_name": presentation,
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
		return new_file.file_url
	return file_url


def update_element_urls(presentation, element):
	attribute = "poster" if element.get("type") == "video" else "src"
	image_url = f"/private{element.get(attribute, '')}"

	if image_url.endswith((".webp", ".svg")):
		return

	image, filename, extn = get_local_image(image_url)

	if can_convert_image(extn):
		new_url = create_new_webp_file_doc(presentation, image_url, image, extn)
		element[attribute] = new_url


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
