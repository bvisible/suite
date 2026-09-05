# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe


def is_thumbnail_path(thumbnail):
    return thumbnail and isinstance(thumbnail, str) and not thumbnail.startswith("data:")


def execute():
    if not frappe.db.has_column("Slide", "thumbnail"):
        return

    presentations = frappe.get_all("Presentation", fields=["name", "thumbnail"])

    for presentation in presentations:
        if presentation.thumbnail:
            continue

        first_slide_thumbnail = frappe.db.get_value(
            "Slide",
            {"parent": presentation.name, "idx": 1},
            "thumbnail",
        )
        if is_thumbnail_path(first_slide_thumbnail):
            frappe.db.set_value(
                "Presentation",
                presentation.name,
                "thumbnail",
                first_slide_thumbnail,
                update_modified=False,
            )
