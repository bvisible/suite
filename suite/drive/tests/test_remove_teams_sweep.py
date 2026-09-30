# //// Neoffice — added file (no upstream equivalent). Covers the marked hunk in
# //// `remove_teams.sweep_sidecars`: an empty `trashed` snapshot is a snapshot, not "not given".
from __future__ import annotations

import unittest
from collections import Counter
from unittest.mock import patch

from suite.drive.patches import remove_teams

SIDECARS = {"team-1": "private/files/alice@example.com"}
DERIVED_TRASHED = {"team-1": {"old.png": "entity-1"}}


class TestSweepSidecars(unittest.TestCase):
    def sweep(self, *args, derived_prefixes=None, derived_trashed=None, **kwargs):
        """Run the sweep with storage and both derivations replaced by mocks.

        `_trashed_by_team` and `_team_prefixes` read `File.team`, a column
        `drop_team_doctypes` has already dropped by the time the job runs: touching
        either when the job carried its own arguments is the bug under test.
        `derived_*` is what a derivation would answer; `args` and `kwargs` go to the sweep.
        """
        with (
            patch.object(remove_teams, "_carry_sidecars", return_value=(Counter(), [])) as carry,
            patch.object(remove_teams, "_team_prefixes", return_value=derived_prefixes or {}) as prefixes,
            patch.object(remove_teams, "_trashed_by_team", return_value=derived_trashed or {}) as trashed,
        ):
            remove_teams.sweep_sidecars(*args, **kwargs)
        return carry, prefixes, trashed

    def test_an_empty_trashed_snapshot_is_not_derived_again(self):
        # A site with nothing in the trash enqueues trashed={}; `or` made that look missing.
        carry, prefixes, trashed = self.sweep(sidecars=SIDECARS, trashed={})

        trashed.assert_not_called()
        prefixes.assert_not_called()
        carry.assert_called_once_with(SIDECARS, {})

    def test_a_snapshot_that_travelled_with_the_job_is_used_as_is(self):
        carry, prefixes, trashed = self.sweep(sidecars=SIDECARS, trashed=DERIVED_TRASHED)

        prefixes.assert_not_called()
        trashed.assert_not_called()
        carry.assert_called_once_with(SIDECARS, DERIVED_TRASHED)

    def test_a_missing_trashed_snapshot_is_derived(self):
        carry, prefixes, trashed = self.sweep(sidecars=SIDECARS, derived_trashed=DERIVED_TRASHED)

        prefixes.assert_not_called()
        trashed.assert_called_once_with()
        carry.assert_called_once_with(SIDECARS, DERIVED_TRASHED)

    def test_a_run_by_hand_derives_both(self):
        # `bench execute ...sweep_sidecars` with no arguments, while `team` is still on File.
        carry, prefixes, trashed = self.sweep(derived_prefixes=SIDECARS, derived_trashed=DERIVED_TRASHED)

        prefixes.assert_called_once_with()
        trashed.assert_called_once_with()
        carry.assert_called_once_with(SIDECARS, DERIVED_TRASHED)

    def test_nothing_to_sweep_touches_no_storage(self):
        carry, _, _ = self.sweep()

        carry.assert_not_called()
