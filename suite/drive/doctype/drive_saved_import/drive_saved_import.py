# //// Neoffice — added file (no upstream equivalent): which file a save of an imported document made (craft.save_import),
# //// so that another app (NeoMail, which copies an attachment into the Drive and opens it) reopens the file its person
# //// saved from that copy, and not another file of the same name (craft.saved_from).
from __future__ import annotations

from frappe.model.document import Document


class DriveSavedImport(Document):
    pass
