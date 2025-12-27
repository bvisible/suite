import frappe

import frappe
from pypika import CustomFunction, Order
from pypika import functions as fn

from drive.utils import get_default_team
from drive.api.permissions import ENTITY_FIELDS, get_user_access
from writer.search import WriterSearch

DriveUser = frappe.qb.DocType("User")
UserGroupMember = frappe.qb.DocType("User Group Member")
DriveFile = frappe.qb.DocType("Drive File")
DrivePermission = frappe.qb.DocType("Drive Permission")
Team = frappe.qb.DocType("Drive Team")
TeamMember = frappe.qb.DocType("Drive Team Member")
DriveFavourite = frappe.qb.DocType("Drive Favourite")
Recents = frappe.qb.DocType("Drive Entity Log")
DriveEntityTag = frappe.qb.DocType("Drive Entity Tag")

Binary = CustomFunction("BINARY", ["expression"])


@frappe.whitelist()
def get_document_list(
    start=0,
    limit=20,
):
    user = frappe.session.user

    # Convert string parameters to integers
    limit = int(limit)
    start = int(start)

    recently_opened = (
        frappe.qb.from_(Recents).select(Recents.entity_name).where(Recents.user == user)
    )

    recent_field = fn.Coalesce(Recents.last_interaction, DriveFile._modified)
    query = (
        frappe.qb.from_(DriveFile)
        .select(
            *ENTITY_FIELDS,
            recent_field.as_("recent"),
        )
        .where((DriveFile.is_active == 1) & (DriveFile.mime_type == "frappe_doc"))
        .where((DriveFile.owner == user) | (DriveFile.name.isin(recently_opened)))
    )

    query = (
        query.left_join(DriveFavourite)
        .on((DriveFavourite.entity == DriveFile.name) & (DriveFavourite.user == user))
        .select(DriveFavourite.name.as_("is_favourite"))
    )

    query = query.left_join(Recents).on(
        (Recents.entity_name == DriveFile.name) & (Recents.user == frappe.session.user)
    )

    query = query.select(Recents.last_interaction.as_("accessed"))

    # Add ordering
    query = query.orderby(recent_field, order=Order.desc)
    # Fetch one extra record to check if there's a next page
    query = query.limit(limit + 1).offset(start)
    res = query.run(as_dict=True)

    # Check if there's a next page
    has_next_page = len(res) > limit

    # Remove the extra record if it exists
    if has_next_page:
        res = res[:limit]

    # Rest of your processing code
    child_count_query = (
        frappe.qb.from_(DriveFile)
        .where((DriveFile.team == get_default_team()) & (DriveFile.is_active == 1))
        .select(DriveFile.parent_entity, fn.Count("*").as_("child_count"))
        .groupby(DriveFile.parent_entity)
    )
    share_query = (
        frappe.qb.from_(DriveFile)
        .right_join(DrivePermission)
        .on(DrivePermission.entity == DriveFile.name)
        .where((DrivePermission.user != "") & (DrivePermission.user != "$TEAM"))
        .select(DriveFile.name, fn.Count("*").as_("share_count"))
        .groupby(DriveFile.name)
    )
    public_files_query = (
        frappe.qb.from_(DrivePermission)
        .where(DrivePermission.user == "")
        .select(DrivePermission.entity)
    )
    team_files_query = (
        frappe.qb.from_(DrivePermission)
        .where(DrivePermission.team == 1)
        .select(DrivePermission.entity)
    )
    public_files = set(k[0] for k in public_files_query.run())
    team_files = set(k[0] for k in team_files_query.run())

    children_count = dict(child_count_query.run())
    share_count = dict(share_query.run())

    default = 0

    for r in res:
        r["children"] = children_count.get(r["name"], 0)
        r["html"] = frappe.get_cached_value("Writer Document", r["doc"], "html")
        if r["name"] in public_files:
            r["share_count"] = -2
        elif default > -1 and (r["name"] in team_files):
            r["share_count"] = -1
        elif default == 0:
            r["share_count"] = share_count.get(r["name"], default)
        else:
            r["share_count"] = default
        r |= get_user_access(r["name"])

    # Return in the format useList expects
    frappe.response["data"] = res
    frappe.response["has_next_page"] = has_next_page


@frappe.whitelist()
def get_versions(id):
    if not get_user_access(id).get("write"):
        frappe.throw("You don't have write access.", frappe.PermissionError)

    doc_name = frappe.db.get_value("Drive File", id, "doc")

    versions = frappe.get_all(
        "Writer Version",
        filters={"doc": doc_name},
        fields=["name", "snapshot", "title", "manual", "creation"],
        order_by="creation asc",
    )

    return versions


@frappe.whitelist()
def search(query, filters=None):
    client = WriterSearch()
    search = client.search(query, filters=filters)
    metadata = get_drive_file_meta([k["name"] for k in search["results"]])
    cleaned_results = []
    for k in search["results"]:
        if k["name"] not in metadata:
            continue
        k.update(metadata[k["name"]])
        cleaned_results.append(k)
    search["results"] = cleaned_results
    return search


def get_drive_file_meta(names, ttl=3600):
    """
    Fetch {name: {title, file_id}} using Redis first, DB as fallback.
    """
    if not names:
        return {}

    cache = frappe.cache()

    keys = {name: f"search:drive_file:{name}" for name in names}
    cached = {"name": cache.get_value(k) for k in keys.values()}

    result = {}
    missing = []
    for name, key in keys.items():
        value = cached.get(key)
        if value:
            result[name] = value
        else:
            missing.append(name)

    if missing:
        rows = frappe.get_all(
            "Drive File",
            filters={"doc": ["in", missing]},
            fields=["name", "title", "doc"],
        )

        for r in rows:
            meta = {
                "title": r["title"],
                "name": r["name"],
            }
            key = f"search:drive_file:{r['name']}"
            cache.set_value(key, meta, expires_in_sec=ttl)
            result[r["doc"]] = meta

    return result
