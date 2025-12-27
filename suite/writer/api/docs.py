from pathlib import Path
import io

import frappe
import markdown
from markdown.extensions.wikilinks import WikiLinkExtension

from drive.utils import (
    create_drive_file,
    default_team,
    get_home_folder,
    get_valid_breadcrumbs,
    get_file_type,
    get_default_team,
)
from drive.api.files import get_new_title
from drive.api.permissions import user_has_permission, ENTITY_FIELDS, get_user_access
from drive.utils.files import FileManager
from drive.utils.users import mark_as_viewed


@frappe.whitelist()
@default_team
def create_document_entity(team, title=None, parent=None, template=None):
    home_directory = get_home_folder(team)
    parent = parent or home_directory.name
    parent_doc = frappe.get_cached_doc("Drive File", parent)
    team = frappe.db.get_value("Drive File", parent, "team")
    if not title:
        title = get_new_title("Untitled Document", parent)

    if not user_has_permission(parent, "upload"):
        frappe.throw(
            "Cannot access folder due to insufficient permissions",
            frappe.PermissionError,
        )

    drive_doc = frappe.new_doc("Writer Document")
    drive_doc.title = title
    if template:
        drive_doc.template = template
    drive_doc.settings = (
        '{"collab": true}'
        if not template
        else '{"collab": true, "template": "' + template + '"}'
    )
    drive_doc.save()

    manager = FileManager()
    path = manager.create_folder(
        frappe._dict(
            {
                "title": title,
                "parent_path": Path(parent_doc.path or ""),
                "team": team,
                "parent_entity": parent_doc.name,
            }
        ),
        home_directory,
    )
    manager.create_folder(
        frappe._dict(
            {
                "title": ".embeds",
                "team": team,
                "parent_path": path,
            }
        ),
        home_directory,
    )

    entity = create_drive_file(
        team,
        title,
        parent,
        "frappe_doc",
        lambda _: path,
        document=drive_doc.name,
    )
    return entity


@frappe.whitelist(allow_guest=True)
def get_document(file_id):
    entity = frappe.db.get_value(
        "Drive File",
        {"is_active": 1, "name": file_id},
        [*ENTITY_FIELDS, "doc"],
        as_dict=1,
    )
    if not entity:
        frappe.throw(
            "We couldn't find what you're looking for.", frappe.DoesNotExistError
        )

    entity["in_home"] = entity.team == get_default_team()
    user_access = get_user_access(entity)
    if user_access.get("read") == 0:
        frappe.throw("You don't have access to this file.", frappe.PermissionError)

    owner_info = (
        frappe.db.get_value(
            "User", entity.owner, ["user_image", "full_name"], as_dict=True
        )
        or {}
    )
    breadcrumbs = {"breadcrumbs": get_valid_breadcrumbs(entity.name, user_access)}
    favourite = frappe.db.get_value(
        "Drive Favourite",
        {
            "entity": file_id,
            "user": frappe.session.user,
        },
        ["entity as is_favourite"],
    )
    mark_as_viewed(entity)
    file_type = get_file_type(entity)
    return_obj = (
        entity
        | user_access
        | owner_info
        | breadcrumbs
        | {"is_favourite": favourite, "file_type": file_type}
    )

    default = 0
    if file_id:
        if get_user_access(file_id, "Guest")["read"]:
            default = -2
        elif get_user_access(file_id, team=1)["read"]:
            default = -1
    return_obj["share_count"] = default
    if entity.mime_type.startswith("text/markdown"):
        return get_markdown_file(entity, return_obj)

    k = frappe.get_doc("Writer Document", entity.doc)
    entity_doc_content = k.as_dict()
    entity_doc_content.pop("name")
    entity_doc_content.pop("owner")
    entity_doc_content.pop("versions")

    return_obj |= entity_doc_content | {
        "modified": entity.modified,
    }
    frappe.response["data"] = return_obj


def get_markdown_file(entity, return_obj):
    manager = FileManager()
    wrapper = io.TextIOWrapper(manager.get_file(entity))
    url_builder = (
        lambda label, base, end: f"/api/method/drive.api.docs.get_wiki_link?team={entity.team}&title={label}"
    )
    with wrapper as r:
        content = r.read()
        md = markdown.Markdown(
            extensions=["extra", "meta", WikiLinkExtension(build_url=url_builder)],
        )
        content = clean_content_for_obsidian(content)
        md.set_output_format("html")
        return_obj["file_content"] = md.convert(content)
        return_obj["properties"] = md.Meta

    frappe.response["data"] = return_obj


def clean_content_for_obsidian(content):
    property_end = content[3:].find("---")
    if content.startswith("---") and property_end != -1:
        content = (
            content[:property_end].replace("\n  ", " " * 4) + content[property_end:]
        )
    content = content[:property_end] + content[property_end:].replace("\n", "\n\n")
    content = content[:property_end] + content[property_end:].replace(
        "\n\n\n", "\n<p></p>"
    )
    return content
