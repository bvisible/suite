# //// Neoffice — added file (no upstream equivalent): the signing secret of the Drive's Office editors, maintained by Neoffice ////
# Copyright (c) 2025, Neoservice and contributors
# For license information, please see license.txt

from __future__ import annotations

import secrets

from frappe.model.document import Document


class WOPISettings(Document):
    def validate(self):
        if not self.jwt_secret:
            self.jwt_secret = secrets.token_hex(32)
