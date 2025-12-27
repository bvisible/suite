import frappe

AAA_SENTINEL = "AAA="


def execute():
    docs = frappe.get_all(
        "Writer Document",
        fields=["name", "html", "collab"],
    )

    for row in docs:
        # a) must have collaboration enabled
        if not row.collab:
            continue

        # b) html must be blank or sentinel
        if row.html and row.html.strip() != AAA_SENTINEL:
            continue

        doc = frappe.get_doc("Writer Document", row.name)

        html = generate_html_for_doc(doc)
        if html:
            frappe.db.set_value(
                "Writer Document",
                doc.name,
                "html",
                html,
                update_modified=False,
            )


def generate_html_for_doc(doc):
    last_version = frappe.db.get_value(
        "Writer Version",
        filters={
            "doc": doc.name,
        },
        fieldname=["snapshot"],
        order_by="creation desc",
        as_dict=True,
    )
    if not last_version:
        print(f"{doc} has no versions so far.")
        return
    return last_version["snapshot"]
