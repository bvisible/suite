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
def rename_presentation(name, new_name):
	nameSlug = slug(new_name)
	frappe.rename_doc("Presentation", name, nameSlug)
	frappe.db.set_value("Presentation", nameSlug, "title", new_name)
	return nameSlug
