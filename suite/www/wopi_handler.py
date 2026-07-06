# //// Neoffice: new file — Collabora/WOPI port (from drive_wopi), maintained by Neoffice ////
"""WOPI URL handler for Collabora Online.

Routes (declared in suite/hooks.py website_route_rules):
- GET  /wopi/files/{file_id}           -> CheckFileInfo
- POST /wopi/files/{file_id}           -> Lock operations
- GET  /wopi/files/{file_id}/contents  -> GetFile
- POST /wopi/files/{file_id}/contents  -> PutFile
"""

from __future__ import annotations

import frappe

no_cache = True


def get_context(context):
    """Handle WOPI requests based on URL path and method."""
    frappe.local.no_cache = True

    path = frappe.request.path
    method = frappe.request.method

    # Path formats: /wopi/files/{file_id} or /wopi/files/{file_id}/contents
    parts = path.strip("/").split("/")

    if len(parts) < 3 or parts[0] != "wopi" or parts[1] != "files":
        return send_error(404, "Invalid WOPI path")

    file_id = parts[2]
    is_contents = len(parts) > 3 and parts[3] == "contents"

    from suite.drive.wopi.endpoints import check_file_info, get_file, handle_lock, put_file

    try:
        if is_contents:
            if method == "GET":
                get_file(file_id)
            elif method == "POST":
                put_file(file_id)
            else:
                return send_error(405, "Method not allowed")
        else:
            if method == "GET":
                check_file_info(file_id)
            elif method == "POST":
                handle_lock(file_id)
            else:
                return send_error(405, "Method not allowed")

    except frappe.AuthenticationError as e:
        return send_error(401, str(e))
    except frappe.PermissionError as e:
        return send_error(403, str(e))
    except frappe.DoesNotExistError as e:
        return send_error(404, str(e))
    except Exception as e:
        frappe.log_error("WOPI Handler Error", str(e))
        return send_error(500, str(e))

    # Response was set by the handler
    raise frappe.Redirect


def send_error(status_code, message):
    """Send an error response."""
    frappe.local.response.http_status_code = status_code
    frappe.local.response["type"] = "json"
    frappe.local.response["message"] = message
    raise frappe.Redirect
