from __future__ import annotations
import frappe


def execute():
    settings = frappe.get_single("Drive Disk Settings")
    settings.flat = True
    settings.save()
