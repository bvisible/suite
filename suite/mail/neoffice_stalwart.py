# //// Neoffice — added file (no upstream equivalent): the mailbox of a new desk user, made on our own Stalwart.
# ////
# //// Upstream moved every change to the mail directory (accounts, domains, groups, lists) behind Suite Cloud, the
# //// control plane of Frappe's hosted Suite (suite/mail/directory.py): a site no longer holds the administrator's
# //// credentials of the mail server, and `suite/mail/stalwart/` is gone. Neoffice runs its own Stalwart and gives
# //// every desk user a mailbox when the user is created (suite/mail/events.py: Mail and Calendar work out of the box,
# //// without a Mail Account Request). This module is that, kept apart from upstream's code so that a merge cannot
# //// reach it: the three calls it needs — the domains, an account, an app password — of Stalwart's management API.
# //// When a desk user is deleted, their mailbox is locked here, its mail kept (lock_account, maintenance#1743).
# ////
# //// That API is a JMAP dialect: capability `urn:stalwart:jmap`, methods prefixed `x:`, calls scoped to the
# //// administrator's own account, authenticated as the administrator (Mail Settings or the site config's `mail`
# //// key: server_url, username, password, verify_ssl). An app password is made as the account itself, through
# //// Stalwart's master-user login `<account>%<administrator>`. The plan: Obsidian, Neoffice/Suite-Adoption/17.
from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import frappe
import httpx
from frappe import _

from suite.utils.dt import utcnow

CORE_URN = "urn:ietf:params:jmap:core"
MANAGEMENT_URN = "urn:stalwart:jmap"
DEFAULT_LOCALE = "en_US"  # Stalwart wants every account to carry a locale
TIMEOUT = httpx.Timeout(30.0, read=60.0)


def _remaining_setting(field: str) -> Any:
    """A value Mail Settings still holds in `tabSingles` though its doctype no longer declares the field (upstream
    dropped `username` and `password`): read straight from the table, since `get_single_value` refuses a field
    the meta does not have. None when there is none."""

    try:
        rows = frappe.db.sql(
            "select value from `tabSingles` where doctype = 'Mail Settings' and field = %s", (field,)
        )
    except Exception:
        return None
    return rows[0][0] if rows else None


def get_admin_config() -> tuple[str | None, str | None, str | None, bool]:
    """(server_url, administrator, password, verify_ssl).

    The site config's `mail` key first. Then Mail Settings, which upstream's doctype no longer has the
    credentials in: the values of an instance that had them stay in the database (the password in __Auth), so an
    instance migrated from before the merge keeps working until they are moved to the site config.

    Never raises: it is read by the hook of every new user (`events.provision_mail_account`), and the mailbox of
    a user must never be the reason a user cannot be made."""

    from frappe.utils.password import get_decrypted_password

    conf = frappe.conf.get("mail") or {}
    server_url = conf.get("server_url") or _remaining_setting("server_url")
    username = conf.get("username") or _remaining_setting("username")
    password = conf.get("password")
    if not password:
        try:
            password = get_decrypted_password(
                "Mail Settings", "Mail Settings", "password", raise_exception=False
            )
        except Exception:
            password = None
    verify = conf.get("verify_ssl")
    if verify is None:
        verify = _remaining_setting("verify_ssl")
    return server_url, username, password, bool(frappe.utils.cint(verify) if verify is not None else 1)


def is_stalwart_configured(raise_exception: bool = False) -> bool:
    """Whether this site holds the credentials to make mailboxes on its own Stalwart."""

    try:
        server_url, username, password, _verify = get_admin_config()
    except Exception:
        server_url = username = password = None
    if server_url and username and password:
        return True

    if raise_exception:
        frappe.throw(_("The Stalwart administrator is not configured on this site."))
    return False


class Management:
    """One administrator session on Stalwart's management API."""

    def __init__(self, login: str | None = None) -> None:
        server_url, username, password, verify = get_admin_config()
        if not (server_url and username and password):
            frappe.throw(_("The Stalwart administrator is not configured on this site."))

        self.admin = username
        self.http = httpx.Client(
            auth=(login or username, password), verify=verify, follow_redirects=True, timeout=TIMEOUT
        )
        try:
            response = self.http.get(urljoin(server_url, "/.well-known/jmap"))
            response.raise_for_status()
            session = response.json()
        except Exception as error:
            self.http.close()
            self._fail(f"session: {error}")

        self.api_url = urljoin(str(response.url), session.get("apiUrl") or "")
        self.account_id = (session.get("primaryAccounts") or {}).get(MANAGEMENT_URN)
        if not self.account_id:
            self.http.close()
            self._fail(f"The server does not advertise {MANAGEMENT_URN} for this administrator.")

    def __enter__(self) -> Management:
        return self

    def __exit__(self, *exc: object) -> None:
        self.http.close()

    @staticmethod
    def _fail(detail: str) -> None:
        # The real cause goes to the error log; the person gets a sentence that gives nothing of the server away.
        frappe.log_error("Stalwart management request failed", detail)
        frappe.throw(_("The mail server could not process this request. Please try again."))

    def call(self, method: str, **arguments: Any) -> dict:
        """One `x:<method>` call, its arguments minus the Nones; the answer's arguments, or a failure."""

        body = {
            "using": [CORE_URN, MANAGEMENT_URN],
            "methodCalls": [
                [
                    f"x:{method}",
                    {"accountId": self.account_id, **{k: v for k, v in arguments.items() if v is not None}},
                    "0",
                ]
            ],
        }
        try:
            response = self.http.post(self.api_url, json=body)
            response.raise_for_status()
            name, result = response.json()["methodResponses"][0][:2]
        except Exception as error:
            self._fail(f"{method}: {error}")

        if name == "error":
            self._fail(f"{method}: {frappe.as_json(result)}")
        for key in ("notCreated", "notUpdated", "notDestroyed"):
            if result.get(key):
                self._fail(f"{method}: {frappe.as_json({key: result[key]})}")
        return result

    def find_id(self, type_: str, filter_: dict) -> str | None:
        """The id of the first `type_` object matching `filter_`, or None."""

        found = self.call(f"{type_}/query", filter=filter_, limit=1)
        return (found.get("ids") or [None])[0]


def get_domains() -> list[dict]:
    """The domains of the server: {id, name, isEnabled}."""

    with Management() as management:
        return management.call("Domain/get", properties=["id", "name", "isEnabled"]).get("list") or []


def create_account(
    name: str,
    domain: str,
    password: str | None = None,
    description: str | None = None,
    aliases: list[str] | None = None,
    groups: list[str] | None = None,
    roles: list[str] | None = None,
    quota: int | None = None,
    locale: str | None = None,
    timezone: str | None = None,
) -> str:
    """A user account, its domain and role names resolved to ids; returns the account's id. Aliases and groups are
    not used here (the provisioning makes none): they are refused rather than silently ignored."""

    if aliases or groups:
        frappe.throw(_("Aliases and groups are not supported when a mailbox is made here."))

    with Management() as management:
        domain_id = management.find_id("Domain", {"name": domain})
        if not domain_id:
            frappe.throw(_("Domain {0} not found on the Stalwart server.").format(domain))

        role_ids = []
        for description_ in roles or []:
            role_id = management.find_id("Role", {"description": description_})
            if not role_id:
                frappe.throw(_("Role {0} does not exist on the Stalwart server.").format(description_))
            role_ids.append(role_id)

        account = {
            "@type": "User",
            "name": name,
            "domainId": domain_id,
            # credentials and memberGroupIds are id-keyed maps on the wire, not arrays
            "credentials": {
                "0": {"@type": "Password", "secret": password or frappe.generate_hash(length=20)}
            },
            "roles": (
                {"@type": "Custom", "roleIds": {role_id: True for role_id in role_ids}}
                if role_ids
                else {"@type": "User"}
            ),
            "quotas": {"maxDiskQuota": quota} if quota is not None else {},
            "description": description,
            "locale": locale or DEFAULT_LOCALE,
            "timeZone": timezone,
        }
        created = management.call("Account/set", create={"0": account})["created"]["0"]
        return created["id"]


def create_app_password(account: str, description: str | None = None) -> str:
    """An app password for `account` (its address), made as the account through the master-user login; returns
    the secret, which the server shows only once."""

    description = description or f"App Password for {frappe.local.site} - {utcnow()}"
    with Management() as admin:
        login = f"{account}%{admin.admin}"

    with Management(login) as management:
        created = management.call(
            "AppPassword/set",
            create={"0": {"description": description, "permissions": {"@type": "Inherit"}}},
        )["created"]["0"]

    if not created.get("secret"):
        frappe.throw(_("The mail server did not return a generated app password."))
    return created["secret"]


def account_id_of(management: Management, address: str) -> str | None:
    """The id of the account whose address is `address`: its name and its domain, both exactly (in any case). None
    when the server has no such account."""

    local, _, domain = address.strip().lower().partition("@")
    if not local or not domain:
        return None
    domain_id = management.find_id("Domain", {"name": domain})
    if not domain_id:
        return None
    ids = management.call("Account/query", filter={"name": local}, limit=100).get("ids") or []
    if not ids:
        return None
    found = management.call("Account/get", ids=ids, properties=["id", "name", "domainId"]).get("list") or []
    return next(
        (
            account["id"]
            for account in found
            if account.get("domainId") == domain_id and (account.get("name") or "").strip().lower() == local
        ),
        None,
    )


def lock_account(address: str) -> bool:
    """Shut every way into the mailbox `address` and keep its mail: its credentials become one password nobody
    holds, which takes its app passwords and keys with them, and what the server still lists as an app password of
    the account is revoked as the account itself. Only the administrator's own login opens it after that; the mail
    it has stays, and so does the mail that still comes. The account is read back: anything left but that one
    password is a failure. Returns False when the server has no such account."""

    address = address.strip().lower()
    with Management() as management:
        admin = management.admin
        if address in {admin.strip().lower(), f"{admin.strip().lower()}@{address.partition('@')[2]}"}:
            frappe.throw(_("The mail server's administrator account is never locked."))
        account_id = account_id_of(management, address)
        if not account_id:
            return False
        management.call(
            "Account/set",
            update={
                account_id: {
                    "credentials": {"0": {"@type": "Password", "secret": frappe.generate_hash(length=40)}}
                }
            },
        )
        read = management.call("Account/get", ids=[account_id], properties=["credentials"]).get("list") or [
            {}
        ]
        left = [(credential or {}).get("@type") for credential in (read[0].get("credentials") or {}).values()]
        if left != ["Password"]:
            management._fail(f"lock {address}: credentials left {left}")

    with Management(f"{address}%{admin}") as mine:
        ids = mine.call("AppPassword/query", limit=200).get("ids") or []
        if ids:
            mine.call("AppPassword/set", destroy=ids)
    return True
