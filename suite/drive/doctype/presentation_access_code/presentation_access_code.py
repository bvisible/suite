# //// Neoffice — added file (no upstream equivalent): a code given with a shared presentation's link to one person
# //// (suite/drive/presentation/api.py new_access_code, enter_with_code): she enters with it, without an e-mail and a
# //// code sent to it (Jérémy, 09.11: « pouvoir lui donner un code »). Only the code's fingerprint is kept.
from __future__ import annotations

from frappe.model.document import Document


class PresentationAccessCode(Document):
    pass
