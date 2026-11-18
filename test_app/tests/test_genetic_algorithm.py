"""Tests for the genetic algorithm."""

import itertools
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

    def test_fitness_function_must_be_supported(self):
        """Reject an unknown distance metric."""
        parameters = {**self.parameters, "fitnessFunction": "manhattan2"}

        with self.assertRaisesRegex(ValueError, "Fitness function must be"):
            GeneticAlgorithm(parameters, self.coordinates)

    def test_island_coordinates_must_match_the_island_count(self):
        """Reject coordinate data that is incomplete or extra."""
        for coordinates in (
            {"A": (0, 0), "B": (1, 1)},
            {**self.coordinates, "F": (5, 5)},
        ):
            with self.subTest(coordinates=coordinates):
                with self.assertRaisesRegex(ValueError, "Island coordinates must match"):
                    GeneticAlgorithm(self.parameters, coordinates)

    def test_tournament_size_is_read_from_parameters(self):
        """Use the tournament size supplied by the caller."""
        parameters = {**self.parameters, "tournamentSize": 4}

        algorithm = GeneticAlgorithm(parameters, self.coordinates)

        self.assertEqual(algorithm.tournament_size, 4)

    def test_tournament_selection_returns_best_sampled_candidate(self):
        """Select the shortest route from the tournament contestants."""
        algorithm = GeneticAlgorithm(
            {**self.parameters, "tournamentSize": 2}, self.coordinates
        )
        ranked_population = [
            {"genes": "ABCDE", "distance": 10},
            {"genes": "ABCED", "distance": 5},
            {"genes": "ABDCE", "distance": 8},
        ]
        contestants = [ranked_population[0], ranked_population[1]]

        with patch(
            "test_app.genetic_algorithm.random.sample", return_value=contestants
        ) as sample:
            selected = algorithm._select_parent(ranked_population)

        self.assertEqual(selected, "ABCED")
        sample.assert_called_once_with(ranked_population, k=2)

    def test_tournament_of_entire_population_selects_best_candidate(self):
        """A full-population tournament always selects the population's best."""
        algorithm = GeneticAlgorithm(
            {**self.parameters, "tournamentSize": self.parameters["boats"]},
            self.coordinates,
        )
        ranked_population = [
            {"genes": "ABCDE", "distance": distance}
            for distance in range(self.parameters["boats"], 0, -1)
        ]

        with patch(
            "test_app.genetic_algorithm.random.sample",
            return_value=ranked_population,
        ) as sample:
            selected = algorithm._select_parent(ranked_population)

        self.assertEqual(selected, ranked_population[-1]["genes"])
        sample.assert_called_once_with(ranked_population, k=len(ranked_population))

    def test_best_individuals_are_preserved_unchanged_by_elitism(self):
        """Copy the configured number of top-ranked tours without modification."""
        algorithm = GeneticAlgorithm(
            {**self.parameters, "elitism": 0.25, "mutationRate": 0},
            self.coordinates,
        )
        routes = [
            "".join(route)
            for route in itertools.islice(
                itertools.permutations("ABCDE"), self.parameters["boats"]
            )
        ]
        ranked_population = [
            {"genes": genes, "distance": distance}
            for distance, genes in enumerate(routes)
        ]

        with (
            patch.object(algorithm, "_select_parent", return_value="EDCBA"),
            patch.object(algorithm, "_mutate", side_effect=lambda genes, rate: genes),
        ):
            next_population = algorithm._next_generation(ranked_population)

        self.assertEqual(algorithm.elite_count, 3)
        self.assertEqual(
            next_population[: algorithm.elite_count],
            [individual["genes"] for individual in ranked_population[:3]],
        )

    def test_crossover_rate_controls_whether_crossover_runs(self):
        """Respect crossover rates at both 0% and 100%."""
        ranked_population = [
            {"genes": "ABCDE", "distance": distance}
            for distance in range(self.parameters["boats"])
        ]

        for crossover_rate, expected_calls in ((0, 0), (1, 6)):
            with self.subTest(crossover_rate=crossover_rate):
                algorithm = GeneticAlgorithm(
                    {
                        **self.parameters,
                        "crossoverRate": crossover_rate,
                        "mutationRate": 0,
                        "elitism": 0,
                    },
                    self.coordinates,
                )
                with (
                    patch.object(
                        algorithm,
                        "_select_parent",
                        side_effect=["ABCDE", "EDCBA"] * 6,
                    ),
                    patch.object(
                        algorithm,
                        "_ordered_crossover",
                        return_value=("ABCDE", "EDCBA"),
                    ) as crossover,
                    patch.object(
                        algorithm, "_mutate", side_effect=lambda genes, rate: genes
                    ),
                ):
                    next_population = algorithm._next_generation(ranked_population)

                self.assertEqual(crossover.call_count, expected_calls)
                self.assertEqual(len(next_population), self.parameters["boats"])

    def test_full_mutation_rate_attempts_mutation_for_every_gene(self):
        """At 100%, attempt a swap for each gene without requiring a changed route."""
        with (
            patch("test_app.genetic_algorithm.random.random", return_value=0.0) as chance,
            patch(
                "test_app.genetic_algorithm.random.choice",
                side_effect=lambda choices: choices[0],
            ) as partner,
        ):
            # pylint: disable-next=protected-access
            GeneticAlgorithm._mutate("ABCDE", 1.0)

        self.assertEqual(chance.call_count, 5)
        self.assertEqual(partner.call_count, 5)

    def test_elitism_zero_and_one_hundred_percent_boundaries(self):
        """Breed the full population at 0% and copy it unchanged at 100%."""
        routes = [
            "".join(route)
            for route in itertools.islice(
                itertools.permutations("ABCDE"), self.parameters["boats"]
            )
        ]
        ranked_population = [
            {"genes": genes, "distance": distance}
            for distance, genes in enumerate(routes)
        ]

        for elitism, expected_elites in ((0, 0), (1, self.parameters["boats"])):
            with self.subTest(elitism=elitism):
                algorithm = GeneticAlgorithm(
                    {
                        **self.parameters,
                        "elitism": elitism,
                        "crossoverRate": 0,
                        "mutationRate": 0,
                    },
                    self.coordinates,
                )
                with (
                    patch.object(algorithm, "_select_parent", return_value="EDCBA") as select,
                    patch.object(
                        algorithm, "_mutate", side_effect=lambda genes, rate: genes
                    ) as mutate,
                ):
                    next_population = algorithm._next_generation(ranked_population)

                self.assertEqual(algorithm.elite_count, expected_elites)
                self.assertEqual(len(next_population), self.parameters["boats"])
                if elitism == 0:
                    self.assertGreater(select.call_count, 0)
                    self.assertGreater(mutate.call_count, 0)
                    self.assertNotEqual(
                        next_population[:1], [ranked_population[0]["genes"]]
                    )
                else:
                    self.assertEqual(
                        next_population,
                        [individual["genes"] for individual in ranked_population],
                    )
                    select.assert_not_called()
                    mutate.assert_not_called()

    def test_run_respects_requested_generation_count(self):
        """Record exactly the number of generations requested."""
        for generation_count in (1, 4):
            with self.subTest(generation_count=generation_count):
                algorithm = GeneticAlgorithm(
                    {**self.parameters, "maxGenerations": generation_count},
                    self.coordinates,
                )

                algorithm.run()

                self.assertEqual(len(algorithm.generation_record), generation_count)

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
