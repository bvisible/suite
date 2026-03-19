import json

import frappe
from pypika import Criterion, CustomFunction, Order
from pypika import functions as fn

from drive.utils import MIME_LIST_MAP, default_team, get_home_folder, FILE_FIELDS, map_ff_to_drive_type
from drive.utils.api import get_default_access
from .permissions import get_user_access, user_has_permission

DriveUser = frappe.qb.DocType("User")
UserGroupMember = frappe.qb.DocType("User Group Member")
DriveFile = frappe.qb.DocType("File")
DrivePermission = frappe.qb.DocType("Drive Permission")
Team = frappe.qb.DocType("Drive Team")
TeamMember = frappe.qb.DocType("Drive Team Member")
DriveFavourite = frappe.qb.DocType("Drive Favourite")
Recents = frappe.qb.DocType("Drive Entity Log")
DriveEntityTag = frappe.qb.DocType("Drive Entity Tag")

Binary = CustomFunction("BINARY", ["expression"])


@frappe.whitelist(allow_guest=True)
@default_team
def files(
    team: str,
    entity_name: str | None = None,
    order_by: str = "modified 1",
    status: int = 1,
    favourites_only: bool = False,
    recents_only: bool = False,
    shared: bool | None = None,
    tag_list: list[str] | str = [],
    file_kinds: list[str] | str = [],
    folders: bool = False,
    only_parent: bool = True,
    search: str = None,
):
    field, ascending = order_by.replace("modified", "_modified").split(" ")

    all_teams = False
    if team == "all":
        all_teams = True
        team = None
    if not entity_name and team:
        entity_name = get_home_folder(team)["name"]

    user = frappe.session.user if frappe.session.user != "Guest" else ""
    entity = frappe.get_doc("File", entity_name)

    # Verify that entity exists and is part of the team
    if not entity:
        frappe.throw(
            f"Not found ({entity_name}) ",
            frappe.exceptions.PageDoesNotExistError,
        )
    # if not entity.is_drive_file:
    #     files = frappe.get_list('File', filters={'folder': entity_name}, fields=FILE_FIELDS)
    #     # Clean up
    #     for k in files:
    #         if k.is_folder:
    #             k.file_type = 'Folder'
    #     return files

    # Ignore team check for site files
    if team and not team == entity.team and entity.is_drive_file:
        frappe.throw("Given team doesn't match the file's team", ValueError)

    # Verify that folder is public or that they have access
    if not user_has_permission(entity, "read"):
        frappe.throw(
            f"You don't have access.",
            frappe.exceptions.PermissionError,
        )

    query = frappe.qb.from_(DriveFile).where((DriveFile.status == status) | (DriveFile.is_drive_file == 0))

    if shared:
        if shared == True:
            cond = (DrivePermission.entity == DriveFile.name) & (DrivePermission.user == frappe.session.user)
        elif shared == "public":
            cond = (DrivePermission.entity == DriveFile.name) & (DrivePermission.user == "")
        # if shared == "with":
        #     teams = get_teams()
        #     cond |= (DrivePermission.team == 1) & (DrivePermission.user.isin(teams))
        query = query.right_join(DrivePermission).on(cond)
    else:
        query = query.left_join(DrivePermission).on(
            (DrivePermission.entity == DriveFile.name) & (DrivePermission.user == user)
        )

    query = query.select(
        *FILE_FIELDS,
        # Used for non-Drive files
        DriveFile.modified,
        DrivePermission.user.as_("shared_team"),
    ).where(fn.Coalesce(DrivePermission.read, 1).as_("read") == 1)

    # Cleaner way?
    if only_parent and (not recents_only and not favourites_only and not shared):
        query = query.where(DriveFile.folder == entity_name)
    elif not all_teams:
        query = query.where((DriveFile.team == team) & (DriveFile.folder != ""))

    # Get favourites data (only that, if applicable)
    if favourites_only:
        query = query.right_join(DriveFavourite)
    else:
        query = query.left_join(DriveFavourite)
    query = query.on((DriveFavourite.entity == DriveFile.name) & (DriveFavourite.user == frappe.session.user)).select(
        DriveFavourite.name.as_("is_favourite")
    )

    if recents_only:
        query = (
            query.right_join(Recents)
            .on((Recents.entity_name == DriveFile.name) & (Recents.user == frappe.session.user))
            .orderby(Recents.last_interaction, order=Order.desc)
        )
    else:
        query = (
            query.left_join(Recents)
            .on((Recents.entity_name == DriveFile.name) & (Recents.user == frappe.session.user))
            .orderby(DriveFile[field], order=Order.asc if ascending else Order.desc)
        )

    if not status:
        query = query.where(DriveFile.owner == frappe.session.user)
    if search:
        # escape wildcards or lower() depending on DB
        query = query.where(DriveFile.file_name.like(f"%{search}%"))

    query = query.select(Recents.last_interaction.as_("accessed"))
    if tag_list:
        tag_list = json.loads(tag_list)
        query = query.left_join(DriveEntityTag).on(DriveEntityTag.parent == DriveFile.name)
        tag_list_criterion = [DriveEntityTag.tag == tags for tags in tag_list]
        query = query.where(Criterion.any(tag_list_criterion))

    file_kinds = json.loads(file_kinds) if not isinstance(file_kinds, list) else file_kinds
    if file_kinds:
        mime_types = []
        for kind in file_kinds:
            mime_types.extend(MIME_LIST_MAP.get(kind, []))
        criterion = [DriveFile.mime_type == mime_type for mime_type in mime_types]
        if "Folder" in file_kinds:
            criterion.append(DriveFile.is_folder == 1)
        query = query.where(Criterion.any(criterion))

    if folders:
        query = query.where(DriveFile.is_folder == 1)
    res = query.run(as_dict=True)

    child_count_query = (
        frappe.qb.from_(DriveFile)
        .where((DriveFile.team == team) & (DriveFile.status == 1))
        .select(DriveFile.folder, fn.Count("*").as_("child_count"))
        .groupby(DriveFile.folder)
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
        frappe.qb.from_(DrivePermission).where(DrivePermission.user == "").select(DrivePermission.entity)
    )
    team_files_query = frappe.qb.from_(DrivePermission).where(DrivePermission.team == 1).select(DrivePermission.entity)
    public_files = set(k[0] for k in public_files_query.run())
    team_files = set(k[0] for k in team_files_query.run())

    children_count = dict(child_count_query.run())
    share_count = dict(share_query.run())

    default = get_default_access(entity_name)

    # Deduplicate
    if shared:
        added = set()
        filtered_list = []
        for r in res:
            if r["name"] not in added:
                filtered_list.append(r)
            added.add(r["name"])
        res = filtered_list

    # Performance hit is wild, manually checking perms each time without cache.
    for r in res:
        r["children"] = children_count.get(r["name"], 0)

        if r["name"] in public_files:
            r["share_count"] = -2
        elif default > -1 and (r["name"] in team_files):
            r["share_count"] = -1
        elif default == 0:
            r["share_count"] = share_count.get(r["name"], default)
        else:
            r["share_count"] = default
        if not r["is_drive_file"]:
            r["file_type"] = map_ff_to_drive_type(r)
        r["modifiable"] = r["is_drive_file"] and not r["special_file"] == "File"
        r["is_attachment"] = r["is_drive_file"] and r["special_file"] == "File"
        r |= get_user_access(r["name"])
    return res
