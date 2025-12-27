from frappe.search.sqlite_search import SQLiteSearch
from frappe.utils import cstr
import frappe


class WriterSearch(SQLiteSearch):
    INDEX_NAME = "writer_search.db"

    INDEX_SCHEMA = {
        "text_fields": ["content", "title"],
        "metadata_fields": ["owner"],
        "tokenizer": "unicode61 remove_diacritics 2 tokenchars '-_'",
    }

    INDEXABLE_DOCTYPES = {
        "Writer Document": {
            "fields": [{"content": "html"}, "owner"],
        },
    }

    def get_search_filters(self):
        return {}
        return {"owner": frappe.session.user}
