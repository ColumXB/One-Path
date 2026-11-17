"""Tests for the genetic algorithm."""

from unittest.mock import patch

from django.test import TestCase

from ..brute_force import BruteForce
from ..genetic_algorithm import GeneticAlgorithm


class GeneticAlgorithmTests(TestCase):
    """Check genetic search, route scoring, and parameter validation."""

    def setUp(self):
        self.parameters = {
            "bruteForce": False,
            "islands": 5,
            "boats": 12,
            "maxGenerations": 3,
            "mutationRate": 0.1,
            "crossoverRate": 0.8,
            "elitism": 0.1,
            "fitnessFunction": "euclidean",
        }
        self.coordinates = {
            "A": (0, 0),
            "B": (3, 0),
            "C": (3, 4),
            "D": (0, 4),
            "E": (1, 2),
        }

    def test_run_generates_valid_population_for_each_generation(self):
        """Verify each generation contains valid ranked tours."""
        algorithm = GeneticAlgorithm(self.parameters, self.coordinates)

        algorithm.run()

        self.assertEqual(len(algorithm.generation_record), 3)
        for generation in algorithm.generation_record:
            self.assertEqual(len(generation["all"]), self.parameters["boats"])
            self.assertLessEqual(
                generation["best"]["distance"],
                generation["median"]["distance"],
            )
            self.assertLessEqual(
                generation["median"]["distance"],
                generation["worst"]["distance"],
            )
            for individual in [
                generation["best"],
                generation["median"],
                generation["worst"],
                *generation["all"],
            ]:
                genes = individual["genes"]
                self.assertEqual(len(genes), self.parameters["islands"])
                self.assertEqual(set(genes), set("ABCDE"))
                self.assertGreaterEqual(individual["distance"], 0)

    def test_distance_includes_return_leg_and_uses_selected_metric(self):
        """Check that both solvers score closed tours using the selected metric."""
        parameters = {**self.parameters, "islands": 3}
        coordinates = {"A": (0, 0), "B": (3, 0), "C": (3, 4)}

        for metric, expected in (("euclidean", 12), ("manhattan", 14), ("chebyshev", 11)):
            with self.subTest(metric=metric):
                options = {**parameters, "fitnessFunction": metric}
                genetic = GeneticAlgorithm(options, coordinates)
                exhaustive = BruteForce({**options, "bruteForce": True}, coordinates)
                self.assertEqual(genetic.calculate_distance("ABC"), expected)
                self.assertEqual(exhaustive.calculate_distance("ABC"), expected)

    def test_pairwise_distance_cache_is_symmetric_and_contains_no_self_legs(self):
        """Verify that the distance cache stores each distinct leg in both directions."""
        parameters = {**self.parameters, "islands": 3}
        coordinates = {"A": (0, 0), "B": (3, 0), "C": (3, 4)}

        algorithm = GeneticAlgorithm(parameters, coordinates)

        # Inspect the cache directly to verify which legs are stored.
        distances = algorithm._pairwise_distances  # pylint: disable=protected-access
        self.assertEqual(distances["A", "B"], 3)
        self.assertEqual(distances["B", "A"], 3)
        self.assertEqual(distances["A", "C"], 5)
        self.assertEqual(len(distances), 3 * 2)
        self.assertNotIn(("A", "A"), distances)

    def test_tournament_size_cannot_exceed_population(self):
        """Reject a tournament larger than the population."""
        parameters = {**self.parameters, "boats": 2, "tournamentSize": 5}

        with self.assertRaisesRegex(ValueError, "tournamentSize must be between 1 and 2"):
            GeneticAlgorithm(parameters, self.coordinates)

    def test_population_size_must_be_at_least_two(self):
        """Reject a population with fewer than two boats."""
        parameters = {**self.parameters, "boats": 1}

        with self.assertRaisesRegex(ValueError, "boats must be between 2 and 100"):
            GeneticAlgorithm(parameters, self.coordinates)

    def test_tournament_size_is_read_from_parameters(self):
        """Use the tournament size supplied by the caller."""
        parameters = {**self.parameters, "tournamentSize": 4}

        algorithm = GeneticAlgorithm(parameters, self.coordinates)

        self.assertEqual(algorithm.tournament_size, 4)

    def test_ordered_crossover_and_swap_mutation_preserve_each_island_once(self):
        """Verify that both genetic operators produce valid tours."""
        parent_one = "ABCDE"
        parent_two = "EDCBA"

        # pylint: disable-next=protected-access
        children = GeneticAlgorithm._ordered_crossover(parent_one, parent_two)
        # pylint: disable-next=protected-access
        mutated = GeneticAlgorithm._mutate(parent_one, 0.5)

        for genes in (*children, mutated):
            self.assertEqual(len(genes), 5)
            self.assertEqual(set(genes), set(parent_one))

    def test_mutation_rate_is_checked_for_each_gene_and_can_make_multiple_swaps(self):
        """Check that one mutation pass can swap several pairs of islands."""
        with (
            patch(
                "test_app.genetic_algorithm.random.random",
                side_effect=[0.0, 0.0, 1.0, 1.0, 1.0],
            ) as mutation_chance,
            patch(
                "test_app.genetic_algorithm.random.choice",
                side_effect=[1, 3],
            ) as swap_partner,
        ):
            # pylint: disable-next=protected-access
            mutated = GeneticAlgorithm._mutate("ABCDE", 0.5)

        self.assertEqual(mutated, "BDCAE")
        self.assertEqual(set(mutated), set("ABCDE"))
        self.assertEqual(mutation_chance.call_count, 5)
        self.assertEqual(swap_partner.call_count, 2)

    def test_zero_mutation_rate_leaves_route_unchanged(self):
        """Keep the original route when mutation is disabled."""
        with patch("test_app.genetic_algorithm.random.random", return_value=0.5):
            # pylint: disable-next=protected-access
            mutated = GeneticAlgorithm._mutate("ABCDE", 0.0)

        self.assertEqual(mutated, "ABCDE")

    def test_get_generation_returns_none_for_unavailable_generation(self):
        """Return no record for unavailable generation indices."""
        algorithm = GeneticAlgorithm(self.parameters, self.coordinates)

        self.assertIsNone(algorithm.get_generation(0))
        self.assertIsNone(algorithm.get_generation(-1))
