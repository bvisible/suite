#//// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
#//// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
from frappe import _


def get_data():
    return [
        {
            "module_name": "Drive",
            "color": "grey",
            "icon": "octicon octicon-file-directory",
            "type": "module",
            "label": _("Drive"),
        }
    ]
