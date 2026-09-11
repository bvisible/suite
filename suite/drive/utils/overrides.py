# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations
import frappe
from frappe.permissions import SYSTEM_USER_ROLE, get_doctypes_with_read

from suite.drive.utils import get_principals, principal_list


def file_permission_criterion(user=None, table=None):
    user = user or frappe.session.user
    roles = frappe.get_roles(user)
    if user == "Administrator" or "Suite Admin" in roles:
        return None

    file = table or frappe.qb.DocType("File")
    permission = frappe.qb.DocType("Drive Permission")
    share = frappe.qb.DocType("DocShare")
    criterion = (
        (file.is_private == 0)
        | (file.owner == user)
        | file.name.isin(
            frappe.qb.from_(permission)
            .select(permission.entity)
            .where(
                permission.user.isin(get_principals(user)) & (permission.read == 1) & (permission.deny == 0)
            )
        )
        | file.name.isin(
            frappe.qb.from_(share)
            .select(share.share_name)
            .where((share.share_doctype == "File") & (share.user == user) & (share.read == 1))
        )
    )
    if SYSTEM_USER_ROLE in roles:
        # //// Neoffice — v15 compat: _doctypes_with_read takes no user arg here (14deec32 "fix(drive): File hook works on Frappe v15 (get_doctypes_with_read signature)"), see block marker below
        criterion |= file.attached_to_doctype.isin(_doctypes_with_read(user) or [""])
    return criterion


# //// Neoffice — v15 compat. Upstream calls get_doctypes_with_read(user) (v16 signature);
# //// on Frappe v15 the function takes no argument and answers for the session user, so
# //// every File listing by a non-admin died in "takes 0 positional arguments but 1 was
# //// given" (the reportview of /app/file, frappe.client.get_list("File")). Drop at v16.
def _doctypes_with_read(user):
    try:
        return get_doctypes_with_read(user)
    except TypeError:
        if user != frappe.session.user:
            # v15 can only answer for the session user: fall back to the safe side
            return None
        return get_doctypes_with_read()


# //// Neoffice — added: render the criterion to SQL HERE, not in the framework.
# //// `permission_query_conditions` hooks are joined with `" and ".join(...)`, so a
# //// hook that returns a pypika term instead of a string kills the join:
# //// "sequence item 1: expected str instance, ComplexCriterion found". Frappe v16
# //// learned to render it (0ae2243ad6, 2026-06-30) and we backported that into our
# //// v15 fork -- but the backport sits in `frappe/model/db_query.py`, a chokepoint
# //// every app's every list query goes through, and `filter_file` is the ONLY hook
# //// of this app that returns a term (the fifteen others return strings). A
# //// divergence in our own app costs less than one in the framework, and this way
# //// the app works on an unpatched v15 too (neoffice-maintenance#263).
# ////
# //// Same rendering as the backport: values are collected through a parameter
# //// wrapper and inlined with `frappe.db.escape` -- the driver's escaping -- rather
# //// than pypika's bare quote-doubling, which is unsafe on MariaDB where backslash
# //// is itself an escape character.
def render_permission_criterion(criterion) -> str:
    """A pypika permission criterion as a namespaced SQL string."""
    from frappe.query_builder.terms import NamedParameterWrapper

    quote_char = "`" if frappe.db.db_type == "mariadb" else '"'
    param_wrapper = NamedParameterWrapper()
    sql = criterion.get_sql(with_namespace=True, quote_char=quote_char, param_wrapper=param_wrapper)
    for key, value in param_wrapper.get_parameters().items():
        sql = sql.replace(f"%({key})s", frappe.db.escape(value))
    return sql


def filter_file(user=None):
    """Replaces the framework's File query conditions (skipped because of the
    `ignore_file_permissions` hook). Conservative: owner, direct Drive grants,
    public files, DocShares, and readable attachments — folder-inherited access
    needs Drive's recursive path traversal, impractical in SQL, so it's left to
    `has_permission`."""
    criterion = file_permission_criterion(user)
    # None = no restriction (Administrator, Suite Admin). The framework skips a
    # falsy condition, and "" says it the way every other hook here says it.
    if criterion is None:
        return ""
    return render_permission_criterion(criterion)


def common_filters(func):
    def decorator(user):
        user = user or frappe.session.user
        if user == "Administrator" or "Suite Admin" in frappe.get_roles(user):
            return ""
        return func(user)

    return decorator


@common_filters
def filter_drive_permission(user):
    user = frappe.db.escape(user)
    return f"""(`tabDrive Permission`.`owner` = {user} or `tabDrive Permission`.user = {user})"""


@common_filters
def filter_drive_settings(user):
    return f"(`tabDrive Settings`.`user` = {frappe.db.escape(user)})"


@common_filters
def filter_drive_invitation(user):
    return f"(`tabDrive User Invitation`.`email` = {frappe.db.escape(user)})"


@common_filters
def filter_activity_log(user):
    escaped = frappe.db.escape(user)
    return (
        f"(`tabDrive Entity Activity Log`.`entity` IN ("
        f"SELECT `name` FROM `tabFile` WHERE `owner` = {escaped}"
        f" UNION SELECT `entity` FROM `tabDrive Permission`"
        f" WHERE `user` IN ({principal_list(user)}) AND `read` = 1 AND `deny` = 0))"
    )


@common_filters
def filter_drive_favourite(user):
    return f"""(`tabDrive Favourite`.`user` = {frappe.db.escape(user)})"""


@common_filters
def filter_drive_recent(user):
    return f"""(`tabDrive Entity Log`.`user` = {frappe.db.escape(user)})"""


@common_filters
def filter_drive_notif(user):
    user = frappe.db.escape(user)
    return f"(`tabDrive Notification`.to_user = {user} or `tabDrive Notification`.from_user = {user})"
