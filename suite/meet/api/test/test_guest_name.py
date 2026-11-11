# //// Neoffice — added file (no upstream equivalent): a guest's name is checked on its letters, any script,
# //// not on ASCII (neoffice-maintenance#1194).
from __future__ import annotations

import unittest

from suite.meet.utils.user import validate_guest_name


class TestGuestName(unittest.TestCase):
    def test_a_name_with_accents_is_let_in(self):
        for name in (
            "Invité",
            "Zoë Müller",
            "François d\u2019Ivernois",
            "Ana-Lucía O'Brien",
            "Łukasz",
            "Ødegård",
        ):
            with self.subTest(name=name):
                self.assertEqual(validate_guest_name(name), (True, None))

    def test_markup_is_still_refused(self):
        for name in ("<b>Bold</b>", "Tom & Jerry", 'Say "hi"', "a/b", "x;y"):
            with self.subTest(name=name):
                self.assertEqual(validate_guest_name(name), (False, "Guest name contains invalid characters"))

    def test_the_length_rules_are_unchanged(self):
        self.assertFalse(validate_guest_name("A")[0])
        self.assertFalse(validate_guest_name("é" * 51)[0])
        self.assertFalse(validate_guest_name("   ")[0])
