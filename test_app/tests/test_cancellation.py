"""Tests for cooperative cancellation in both solvers."""

from unittest.mock import patch

from django.test import TestCase

from ..brute_force import BruteForce
from ..genetic_algorithm import GeneticAlgorithm
from ..route_search import SearchCancelled


class CancellationTests(TestCase):
    """Check cooperative cancellation in both solver loops."""

    def setUp(self):
        self.islands = {"A": (0, 0), "B": (3, 4), "C": (3, 0), "D": (0, 4)}
        self.parameters = {
            "bruteForce": False, "islands": 4, "boats": 6, "maxGenerations": 3,
            "mutationRate": 0.1, "crossoverRate": 0.8, "elitism": 0.1,
            "fitnessFunction": "euclidean",
        }

    def test_cancel_before_start_is_honoured_and_solver_can_run_again(self):
        """Keep early cancellation requests and allow a fresh run afterwards."""
        for solver in (GeneticAlgorithm, BruteForce):
            with self.subTest(solver=solver.__name__):
                algorithm = solver(self.parameters, self.islands)
                algorithm.cancel()

                with self.assertRaises(SearchCancelled):
                    algorithm.run()

                self.assertEqual(algorithm.get_generations_after(-1), [])
                algorithm.run()
                self.assertTrue(algorithm.get_generations_after(-1))

    def test_brute_force_stops_between_candidate_tours(self):
        """Stop enumeration after cancellation while preserving earlier progress."""
        algorithm = BruteForce(self.parameters, self.islands)
        original_distance = algorithm.calculate_distance

        def cancel_after_candidate(genes):
            distance = original_distance(genes)
            algorithm.cancel()
            return distance

        with patch.object(algorithm, "calculate_distance", side_effect=cancel_after_candidate):
            with self.assertRaises(SearchCancelled):
                algorithm.run()

        self.assertEqual(len(algorithm.get_generations_after(-1)), 1)

    def test_genetic_search_stops_before_breeding_another_generation(self):
        """Keep the completed generation and honour a cancellation request."""
        algorithm = GeneticAlgorithm(self.parameters, self.islands)
        # pylint: disable-next=protected-access
        evaluate = algorithm._evaluate_population

        def cancel_after_evaluation(population):
            ranked = evaluate(population)
            algorithm.cancel()
            return ranked

        with patch.object(algorithm, "_evaluate_population", side_effect=cancel_after_evaluation):
            with self.assertRaises(SearchCancelled):
                algorithm.run()

        self.assertEqual(len(algorithm.get_generations_after(-1)), 1)
