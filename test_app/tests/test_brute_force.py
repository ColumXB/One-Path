"""Tests for the exhaustive search."""

from django.test import TestCase

from ..brute_force import BruteForce


class BruteForceTests(TestCase):
    """Check exhaustive search progress, results, and limits."""

    def setUp(self):
        self.parameters = {"bruteForce": True, "islands": 4, "fitnessFunction": "euclidean"}
        self.islands = {"A": (0, 0), "B": (3, 4), "C": (3, 0), "D": (0, 4)}

    def test_run_records_improvements_and_finds_shortest_closed_tour(self):
        """Report each shorter tour and finish at the known optimum."""
        algorithm = BruteForce(self.parameters, self.islands)

        algorithm.run()

        updates = algorithm.get_generations_after(-1)
        self.assertEqual(
            [(number, record["best"]) for number, record in updates],
            [
                (0, {"genes": "ABCD", "distance": 18}),
                (1, {"genes": "ABDC", "distance": 16}),
                (2, {"genes": "ACBD", "distance": 14}),
            ],
        )
        for _, record in updates:
            self.assertIsNone(record["median"])
            self.assertIsNone(record["worst"])

    def test_boat_count_has_no_effect_and_rerun_resets_progress(self):
        """Ignore boat settings and start with fresh progress on each run."""
        algorithm = BruteForce({**self.parameters, "boats": 0}, self.islands)
        baseline = BruteForce(self.parameters, self.islands)
        baseline.run()

        algorithm.run()
        algorithm.run()

        self.assertEqual(algorithm.get_generations_after(-1), baseline.get_generations_after(-1))

    def test_rejects_more_than_twelve_islands(self):
        """Reject inputs above the exhaustive search limit."""
        islands = {chr(65 + index): (index, 0) for index in range(13)}

        with self.assertRaisesRegex(ValueError, "islands must be between 3 and 12"):
            BruteForce({**self.parameters, "islands": 13}, islands)

    def test_accepts_twelve_islands(self):
        """Accept the full slider range without starting an exhaustive search."""
        islands = {chr(65 + index): (index, 0) for index in range(12)}

        algorithm = BruteForce({**self.parameters, "islands": 12}, islands)

        self.assertEqual(algorithm.num_nodes, 12)
