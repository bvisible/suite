# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from __future__ import annotations
class OwnerFromUser:
    """Pin ``owner`` to the record's ``user`` field on insert.

    The Suite User role grants access through Frappe's ``if_owner``, which keys off the
    standard ``owner`` (created-by) field rather than the doctype's own ``user`` field.
    Records provisioned by an admin or a background job would otherwise be owned by
    whoever ran the code and stay hidden from the user they belong to. Setting
    ``owner = user`` keeps ``if_owner`` aligned with the intended user regardless of who
    actually created the record.

    Mix in *before* ``Document`` so this ``before_insert`` is picked up:
    ``class Foo(OwnerFromUser, Document): ...``
    """

    def before_insert(self) -> None:
        if getattr(self, "user", None):
            self.owner = self.user

        # Cooperative multiple inheritance: forward to any before_insert further down the
        # MRO (e.g. another mixin ordered after this one). Frappe resolves before_insert via
        # a single getattr, so a mixin that swallows the call would silently skip the rest of
        # the chain. Document defines none, so the call is guarded.
        super_before_insert = getattr(super(), "before_insert", None)
        if callable(super_before_insert):
            super_before_insert()
