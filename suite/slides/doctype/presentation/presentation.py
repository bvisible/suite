# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Presentation(Document):
	def autoname(self):
		self.name = slug(self.title)


def slug(text):
	return text.lower().replace(" ", "-")


@frappe.whitelist()
def get_all_presentations():
	presentations = frappe.get_all("Presentation", fields=["name"], order_by="modified desc")
	all_presentations = [
		frappe.get_doc("Presentation", presentation.name).as_dict() for presentation in presentations
	]
	return all_presentations


@frappe.whitelist()
def get_presentation(name):
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
def rename_presentation(name, new_name):
	name_slug = slug(new_name)
	frappe.rename_doc("Presentation", name, name_slug)
	frappe.db.set_value("Presentation", name_slug, "title", new_name)
	return name_slug


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
