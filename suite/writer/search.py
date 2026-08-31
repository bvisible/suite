from __future__ import annotations
import frappe
from frappe.search.sqlite_search import SQLiteSearch
from frappe.utils import cstr


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
        # No index-level filter: shared documents must stay searchable.
        # Results are permission-filtered in suite.writer.api.general.search.
        return {}
