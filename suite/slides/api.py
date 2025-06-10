import mimetypes
import os

import frappe
from frappe import _
from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.wrappers import Response


def get_file_size(file_path):
	return os.path.getsize(file_path)


def get_range(range_header, file_size):
	import re

	range_start, range_end = 0, None
	match = re.search(r"bytes=(\d+)-(\d*)", range_header)

	if match:
		range_start = int(match.group(1))
		if match.group(2):
			range_end = int(match.group(2))

	range_end = range_end or file_size - 1

	return range_start, range_end


def get_file_data(file_path, range_start=0, range_end=None):
	with open(file_path, "rb") as f:
		f.seek(range_start)
		if range_end is not None:
			# read the specified range from the file
			data = f.read(range_end - range_start + 1)
		else:
			# return the full file content in the response
			data = f.read()
	return data


def get_response(src):
	file_path = frappe.get_site_path() + src
	file_size = get_file_size(file_path)
	mimetype = mimetypes.guess_type(file_path)[0] or "video/mp4"

	range_header = frappe.request.headers.get("Range", None)

	response = None

	# if the request includes a Range header, return a partial content response
	if range_header:
		# extract the byte range from the Range header
		range_start, range_end = get_range(range_header, file_size)
		file_data = get_file_data(file_path, range_start, range_end)
		response = Response(file_data, 206, mimetype=mimetype, direct_passthrough=True)
		response.headers["Content-Range"] = f"bytes {range_start}-{range_end}/{file_size}"
		content_length = range_end - range_start + 1

	# otherwise, return the full content response
	else:
		file_data = get_file_data(file_path)
		response = Response(file_data, 200, mimetype=mimetype, direct_passthrough=True)
		content_length = file_size

	response.headers["Content-Length"] = str(content_length)
	response.headers["Accept-Ranges"] = "bytes"
	return response


@frappe.whitelist()
def get_video_file(src):
	file_doc = frappe.get_doc("File", {"file_url": src})

	if not file_doc:
		raise NotFound

	if not frappe.has_permission("File", "read", file_doc):
		raise Forbidden(_("You don't have permission to access this file"))

	return get_response(src)
