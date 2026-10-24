# //// Neoffice — added file (no upstream equivalent).
# //// Translation anchors: strings `bench generate-pot-file` cannot see on its own.
"""Translation anchors.

The extractor reads DocType JSON files WITHOUT a context, so the "Store" label of the Store
Entry and Mail Cluster Store DocTypes lands in the POT as the bare key. The bare key is shared by
the whole site (webshop means "Boutique" by it), while the desk looks a DocType label up as
"<label>:<DocType>" first. The contextual entries of `locale/fr.po` only survive
`bench update-po-files` if the POT also carries them, which is what this module is for.

This function is never called: it exists so the extractor finds the strings.
"""

# //// Neoffice — Python 3.12 graft (upstream targets 3.14, where PEP 649 makes
# //// annotations lazy): without it `"X" | None` raises TypeError. Drop it at 3.14.
from __future__ import annotations

from frappe import _


def _i18n_anchors():
    """Never called. See the module docstring."""
    _("Store", context="Store Entry")
    _("Store", context="Mail Cluster Store")
    # The tab title of the setup page: the router passes it to __() at run time (frontend/src/router/index.ts).
    _("Set up Neoffice")
    # frappe-ui's calendar grid, which frontend/neoffice-calendar-i18n.ts passes through __() at build time: the
    # extractor never reads node_modules (maintenance#1321).
    _("{0} more")
    # The last stage of a Meet Recording's finalization: the bare « Terminal » is another app's kiosk (« Borne »), and
    # the desk looks a Select option up under its DocType first (ControlSelect and the Select formatter).
    _("Terminal", context="Meet Recording")
