import json

import frappe


def execute():
	presentations = frappe.get_all("Presentation", pluck="name")

	for presentation in presentations:
		doc = frappe.get_doc("Presentation", presentation)

		for slide in doc.slides:
			if slide.thumbnail and slide.thumbnail.startswith("/private"):
				slide.thumbnail = slide.thumbnail.replace("/private", "")

			elements = json.loads(slide.elements or "[]")

			for element in elements:
				if element.get("type") in ("image", "video"):
					url = element.get("src", "")
					if url.startswith("/private"):
						element["src"] = url.replace("/private", "")

					if element.get("poster", "").startswith("/private"):
						element["poster"] = element["poster"].replace("/private", "")

			slide.elements = json.dumps(elements, indent=2)

		doc.save()
