import os

import frappe
from frappe import _
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


def get_media_response_with_range(range_header, file_path):
	file_size = get_file_size(file_path)

	# extract the byte range from the Range header
	range_start, range_end = get_range(range_header, file_size)

	content_length = range_end - range_start + 1

	# read the specified range from the file
	with open(file_path, "rb") as f:
		f.seek(range_start)
		data = f.read(content_length)

		# return a 206 Partial Content response with the specified range
	response = Response(data, 206, mimetype="video/mp4", direct_passthrough=True)
	response.headers["Content-Range"] = f"bytes {range_start}-{range_end}/{file_size}"
	response.headers["Accept-Ranges"] = "bytes"
	response.headers["Content-Length"] = str(content_length)
	return response


def get_media_response(file_path):
	file_size = get_file_size(file_path)

	with open(file_path, "rb") as f:
		data = f.read()

		# return the full file content in the response
	response = Response(data, 200, mimetype="video/mp4", direct_passthrough=True)
	response.headers["Content-Length"] = str(file_size)
	response.headers["Accept-Ranges"] = "bytes"
	return response


@frappe.whitelist()
def get_video_file(src):
	file_path = frappe.get_site_path() + src

	if not os.path.exists(file_path):
		frappe.throw(_("File {0} does not exist").format(file_path), IOError)

	range_header = frappe.request.headers.get("Range", None)

	# if the request includes a Range header, return a partial content response
	if range_header:
		return get_media_response_with_range(range_header, file_path)

	# otherwise, return the full content response
	return get_media_response(file_path)
