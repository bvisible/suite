# //// Neoffice — added file (no upstream equivalent): the sites Nora also reads for a shared presentation
# //// (suite/drive/presentation/sources.py): which pages of a sitemap are read, what a question takes from them, and a
# //// page that did not change is not fetched again. No network: the site is a dictionary of answers.
from __future__ import annotations

import os
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from suite.drive.presentation import sources

ROOT = "https://www.example-firm.ch"
SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://example-firm.ch/fr/comptabilite</loc><lastmod>2026-11-01</lastmod></url>
<url><loc>https://example-firm.ch/en/accounting</loc><lastmod>2026-11-01</lastmod></url>
<url><loc>https://example-firm.ch/fr/tarifs</loc><lastmod>2026-11-01</lastmod></url>
<url><loc>https://example-firm.ch/fr/hebergement</loc><lastmod>2026-11-01</lastmod></url>
<url><loc>https://elsewhere.example.com/fr/autre</loc></url>
</urlset>"""
FILLER = " Le reste de la page parle d'autre chose, pour qu'elle soit assez longue pour être lue." * 4
PAGES = {
    "https://example-firm.ch/fr/comptabilite": "<html><head><title>La comptabilité — Example</title></head><body>"
    "<nav>Menu Accueil Tarifs</nav><main><h1>La comptabilité</h1><p>Les anciens exercices repris de WinBiz sont "
    "archivés et verrouillés, à part de la comptabilité courante.</p>"
    + FILLER
    + "</main><footer>Pied</footer>"
    "</body></html>",
    "https://example-firm.ch/fr/hebergement": "<html><head><title>Hébergement</title></head><body><main>"
    "<p>Vos données restent en Suisse, dans notre centre de calcul de Genève. L'hébergement coûte 149 francs par "
    "mois.</p>" + FILLER + "</main></body></html>",
    "https://example-firm.ch/fr/tarifs": "<html><body><main><p>Dès 49 CHF par mois.</p>"
    + FILLER
    + "</main></body></html>",
    "https://example-firm.ch/en/accounting": "<html><body><main><p>Accounting in English.</p>"
    + FILLER
    + "</main></body></html>",
}


def fake_get(fetched: list):
    def get(url):
        fetched.append(url)
        if url.endswith("/sitemap.xml"):
            return SimpleNamespace(status_code=200, content=SITEMAP.encode(), text=SITEMAP, headers={})
        html = PAGES.get(url)
        if html is None:
            return SimpleNamespace(
                status_code=404, content=b"", text="", headers={"Content-Type": "text/html"}
            )
        return SimpleNamespace(
            status_code=200,
            content=html.encode(),
            text=html,
            headers={"Content-Type": "text/html; charset=utf-8"},
        )

    return get


class TestQuery(TestCase):
    def test_a_question_keeps_its_words_each_by_its_stem(self):
        query = sources.fts_query("L'historique des écritures WinBiz, il va dans l'archive ?")
        self.assertIn('"historiqu"*', query)
        self.assertIn('"ecritur"*', query)  # the index forgets the accents
        self.assertIn('"winbiz"*', query)
        self.assertNotIn('"des"', query)
        self.assertEqual(sources.fts_query("et le la ?"), "")
        # 09.11: « valide » was searched as a whole word and missed « Valider »
        self.assertEqual(sources.stem_of("valide"), "valid")
        self.assertEqual(sources.stem_of("fournisseurs"), "fourniss")
        self.assertEqual(sources.stem_of("payer"), "payer")  # never shorter than four letters

    def test_the_clients_word_brings_the_manuals(self):
        self.assertIn('"devi"*', sources.fts_query("Comment faire une offre ?"))
        self.assertIn('"article"*', sources.fts_query("Comment ajouter un produit ?"))
        self.assertIn('"impression"*', sources.fts_query("Changer la mise en page de nos factures ?"))
        # the answerer reads the software's word beside the client's
        self.assertEqual(
            sources.glossed("Comment faire une offre ?"), "Comment faire une offre ? (offre = devis)"
        )
        self.assertEqual(sources.glossed("Combien de comptes ?"), "Combien de comptes ?")

    def test_the_addresses_are_cleaned(self):
        link = frappe._dict(nora_sites="neoffice.ch/\nhttps://wiki.neoffice.ch/wiki/manuel/\n\nneoffice.ch")
        self.assertEqual(
            sources.roots_of(link), ["https://neoffice.ch", "https://wiki.neoffice.ch/wiki/manuel"]
        )


class TestSite(FrappeTestCase):
    def tearDown(self):
        path = sources.index_path(ROOT)
        if os.path.exists(path):
            os.remove(path)

    def test_a_site_is_read_in_the_links_language_without_its_prices_and_answers_a_question(self):
        fetched = []
        with patch.object(sources, "_get", side_effect=fake_get(fetched)):
            state = sources.refresh(ROOT, "fr")
        self.assertEqual(
            state["pages"], 2
        )  # the French pages, not the prices, not the English, not another host
        self.assertNotIn("https://example-firm.ch/fr/tarifs", fetched)
        self.assertNotIn("https://example-firm.ch/en/accounting", fetched)
        link = frappe._dict(nora_sites=ROOT)
        found = sources.search(link, "L'historique des écritures WinBiz va-t-il dans l'archive ?")
        self.assertEqual(found[0]["url"], "https://example-firm.ch/fr/comptabilite")
        self.assertEqual(found[0]["id"], "W1")
        self.assertIn("archivés et verrouillés", found[0]["text"])
        self.assertNotIn("Menu Accueil", found[0]["text"])  # a page's menus are not read
        self.assertEqual(sources.label(found[0]), "example-firm.ch · La comptabilité")
        hosting = sources.search(link, "Où sont mes données, en Suisse ?")[0]
        self.assertEqual(hosting["url"], "https://example-firm.ch/fr/hebergement")
        # a sentence that states an amount never reaches Nora, whatever the page (a price stays with the presenter)
        self.assertIn("centre de calcul de Genève", hosting["text"])
        self.assertNotIn("149", hosting["text"])

    def test_a_page_whose_title_holds_the_question_comes_before_the_pages_that_only_say_its_words(self):
        root = "https://manual.example-firm.ch"
        filler = " Le reste de la page parle d'autre chose, pour qu'elle soit assez longue pour être lue." * 4
        pages = {
            f"{root}/fr/factures-vente-creer": (
                "Créer une facture de vente",
                "La facture, la facture, la facture.",
            ),
            f"{root}/fr/factures-liste": (
                "Les factures",
                "Une facture de plus, chaque facture, toutes les factures.",
            ),
            f"{root}/fr/relances": ("Relancer un client en retard", "Une facture impayée se relance."),
            f"{root}/fr/valider": (
                "Valider, imprimer (QR) et envoyer une facture",
                "Le bouton Valider fige la facture.",
            ),
        }
        sitemap = "<urlset>" + "".join(f"<url><loc>{u}</loc></url>" for u in pages) + "</urlset>"

        def get(url):
            if url.endswith("/sitemap.xml"):
                return SimpleNamespace(status_code=200, content=sitemap.encode(), text=sitemap, headers={})
            title, body = pages[url]
            html = f"<html><head><title>{title}</title></head><body><main><h1>{title}</h1><p>{body}</p>{filler}</main></body></html>"
            return SimpleNamespace(
                status_code=200, content=html.encode(), text=html, headers={"Content-Type": "text/html"}
            )

        try:
            with patch.object(sources, "_get", side_effect=get):
                sources.refresh(root, "fr")
            link = frappe._dict(nora_sites=root)
            first = lambda question: sources.search(link, question)[0]["url"]  # noqa: E731
            self.assertEqual(first("comment on valide une facture ?"), f"{root}/fr/valider")
            self.assertEqual(
                first("Comment envoyer un rappel pour une facture impayée ?"), f"{root}/fr/relances"
            )
            urls = [p["url"] for p in sources.search(link, "Comment créer une facture ?")]
            self.assertEqual(len(urls), len(set(urls)))  # one place per page
        finally:
            if os.path.exists(sources.index_path(root)):
                os.remove(sources.index_path(root))

    def test_a_page_that_did_not_change_is_not_fetched_again(self):
        with patch.object(sources, "_get", side_effect=fake_get([])):
            sources.refresh(ROOT, "fr")
        fetched = []
        with patch.object(sources, "_get", side_effect=fake_get(fetched)):
            state = sources.refresh(ROOT, "fr")
        self.assertEqual(fetched, ["https://www.example-firm.ch/sitemap.xml"])
        self.assertEqual(state["pages"], 2)
