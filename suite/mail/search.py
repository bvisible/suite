import json
import re
from collections import defaultdict
from contextlib import suppress
from math import isclose

import frappe
import redis
from frappe.utils import cstr, strip_html_tags
from frappe.utils.synchronization import filelock
from redis.commands.search.field import TextField
from redis.commands.search.index_definition import IndexDefinition
from redis.commands.search.query import Query
from redis.exceptions import ResponseError


class Search:
	def __init__(self) -> None:
		self.ft = redis.Redis(host="localhost", port=6379).ft("email_message_idx")

	def build_index(self):
		self.drop_index()
		self.create_index()
		recipients = self.get_recipients()
		for doc in self.get_messages():
			if doc_recipients := recipients.get(doc.name):
				doc["recipients"] = ", ".join(
					[
						f"{d.get('display_name')} <{d.get('email')}>"
						if d.get("display_name")
						else d.get("email")
						for d in doc_recipients
					]
				)
			self.index_doc(doc)

	def drop_index(self):
		with suppress(ResponseError):
			self.ft.dropindex(delete_documents=True)

	def create_index(self):
		definition = IndexDefinition(prefix=["email_message"])
		schema = [
			TextField("subject", weight=12),
			TextField("html_body", weight=5),
			TextField("text_body", weight=5),
			TextField("from_name", weight=2),
			TextField("from_email", weight=2, no_stem=True),
			TextField("recipients", weight=2),
			TextField("account"),
		]
		self.ft.create_index(schema, definition=definition)
		self._index_exists = True

	def get_messages(self):
		return frappe.get_all(
			"Email Message",
			filters={"destroyed": 0},
			fields=[
				"name",
				"subject",
				"html_body",
				"text_body",
				"account",
				"from_name",
				"from_email",
				"thread_id",
				"mailbox_role",
				"received_at",
			],
		)

	def get_recipients(self):
		recipients = frappe.get_all("Email Message Recipient", fields=["email", "display_name", "parent"])
		recipients_map = defaultdict(list)
		for r in recipients:
			recipients_map[r.pop("parent")].append(r)
		return recipients_map

	def index_doc(self, doc):
		if not self.index_exists():
			return

		key = f"email_message:{doc.name}"
		mapping = {
			"subject": cstr(doc.subject),
			"html_body": cstr(strip_html_tags(doc.html_body or "")),
			"text_body": cstr(doc.text_body),
			"account": cstr(doc.account),
			"from_name": cstr(doc.from_name),
			"from_email": cstr(doc.from_email),
			"recipients": cstr(doc.recipients),
			"thread_id": cstr(doc.thread_id),
			"mailbox_role": cstr(doc.mailbox_role),
			"received_at": cstr(doc.received_at),
		}
		self.ft.add_document(key, replace=True, **mapping)

	def index_exists(self):
		if hasattr(self, "_index_exists"):
			return self._index_exists
		self._index_exists = False
		with suppress(ResponseError):
			ftinfo = self.ft.info()
			if isclose(int(ftinfo["num_docs"]), self.get_count("Email Message"), rel_tol=0.1):
				self._index_exists = True
		return self._index_exists

	def search(self, input):
		cleaned_input = re.sub(r"\s+", " ", re.sub(r"[\[\]{}<>+!\-*@.,]", " ", input.strip())).lower()

		query_parts = []
		for word in cleaned_input.split():
			query_parts.append(f"({word}* | %{word}%)")

		fuzzy_query = " ".join(query_parts)

		query = (
			Query(f'@account:"{frappe.session.user}" {fuzzy_query}')
			.paging(0, 10)
			.summarize(fields=["html_body", "text_body"])
			.scorer("DISMAX")
		)

		result = self.ft.search(query)
		out = frappe._dict(docs=[], total=result.total, duration=result.duration)

		for doc in result.docs:
			_doc = frappe._dict(doc.__dict__)
			_doc.id = doc.id.split(":", 1)[1]
			_doc.payload = json.loads(doc.payload) if doc.payload else None
			out.docs.append(_doc)

		return out

	def remove_doc(self, doc):
		if not self.index_exists():
			return

		key = f"email_message:{doc.name}"
		self.ft.delete_document(key)


@frappe.whitelist()
@filelock("email_search_indexing", timeout=300)  # 5 minute timeout for large mailboxes
def build_index():
	"""Build the email search index"""
	frappe.cache().set_value("email_search_indexing_in_progress", True)
	try:
		search_engine = Search()
		search_engine.build_index()
	finally:
		frappe.cache().set_value("email_search_indexing_in_progress", False)


def build_index_in_background():
	"""Queue index building in background"""
	if not frappe.cache().get_value("email_search_indexing_in_progress"):
		frappe.enqueue(build_index, queue="long")


def build_index_if_not_exists():
	"""Build index if it doesn't exist"""
	search_engine = Search()
	if not search_engine.index_exists():
		build_index_in_background()


def on_email_message_after_insert(doc):
	"""Hook to index new emails"""

	search_engine = Search()
	search_engine.index_doc(doc)


def on_email_message_on_update(doc):
	"""Hook to update indexed emails"""

	search_engine = Search()
	search_engine.index_doc(doc)


def on_email_message_on_trash(doc):
	"""Hook to remove emails from index when deleted"""

	search_engine = Search()
	search_engine.remove_doc(doc)
