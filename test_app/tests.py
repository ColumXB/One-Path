import json
import threading
import time
from unittest.mock import patch

from django.test import TestCase

from .genetic_algorithm import genetic_algorithm


class AdminPageTests(TestCase):
    def test_admin_login_page_is_available(self):
        response = self.client.get('/admin/login/')

        self.assertEqual(response.status_code, 200)


class GeneticAlgorithmTests(TestCase):
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
        algorithm = genetic_algorithm(self.parameters, self.coordinates)

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
        parameters = {
            **self.parameters,
            "islands": 3,
            "fitnessFunction": "euclidean",
        }
        coordinates = {"A": (0, 0), "B": (3, 0), "C": (3, 4)}

        euclidean = genetic_algorithm(parameters, coordinates)
        manhattan = genetic_algorithm(
            {**parameters, "fitnessFunction": "manhattan"}, coordinates
        )
        chebyshev = genetic_algorithm(
            {**parameters, "fitnessFunction": "chebyshev"}, coordinates
        )

        self.assertEqual(euclidean.calculate_distance("ABC"), 12)
        self.assertEqual(manhattan.calculate_distance("ABC"), 14)
        self.assertEqual(chebyshev.calculate_distance("ABC"), 11)

    def test_pairwise_distance_cache_is_symmetric_and_contains_no_self_legs(self):
        parameters = {**self.parameters, "islands": 3}
        coordinates = {"A": (0, 0), "B": (3, 0), "C": (3, 4)}

        algorithm = genetic_algorithm(parameters, coordinates)

        self.assertEqual(algorithm._pairwise_distances["A", "B"], 3)
        self.assertEqual(algorithm._pairwise_distances["B", "A"], 3)
        self.assertEqual(algorithm._pairwise_distances["A", "C"], 5)
        self.assertEqual(len(algorithm._pairwise_distances), 3 * 2)
        self.assertNotIn(("A", "A"), algorithm._pairwise_distances)

    def test_tournament_size_cannot_exceed_population(self):
        parameters = {
            **self.parameters,
            "boats": 2,
            "tournamentSize": 5,
        }

        with self.assertRaisesRegex(
            ValueError, "tournamentSize must be between 1 and 2"
        ):
            genetic_algorithm(parameters, self.coordinates)

    def test_population_size_must_be_at_least_two(self):
        parameters = {**self.parameters, "boats": 1}

        with self.assertRaisesRegex(ValueError, "boats must be between 2 and 100"):
            genetic_algorithm(parameters, self.coordinates)

    def test_tournament_size_is_read_from_parameters(self):
        parameters = {**self.parameters, "tournamentSize": 4}

        algorithm = genetic_algorithm(parameters, self.coordinates)

        self.assertEqual(algorithm.tournament_size, 4)

    def test_ordered_crossover_and_swap_mutation_preserve_each_island_once(self):
        parent_one = "ABCDE"
        parent_two = "EDCBA"

        children = genetic_algorithm._ordered_crossover(parent_one, parent_two)
        mutated = genetic_algorithm._mutate(parent_one, 0.5)

        for genes in (*children, mutated):
            self.assertEqual(len(genes), 5)
            self.assertEqual(set(genes), set(parent_one))

    def test_mutation_rate_is_checked_for_each_gene_and_can_make_multiple_swaps(self):
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
            mutated = genetic_algorithm._mutate("ABCDE", 0.5)

        self.assertEqual(mutated, "BDCAE")
        self.assertEqual(set(mutated), set("ABCDE"))
        self.assertEqual(mutation_chance.call_count, 5)
        self.assertEqual(swap_partner.call_count, 2)

    def test_zero_mutation_rate_leaves_route_unchanged(self):
        with patch("test_app.genetic_algorithm.random.random", return_value=0.5):
            mutated = genetic_algorithm._mutate("ABCDE", 0.0)

        self.assertEqual(mutated, "ABCDE")

    def test_get_generation_returns_none_for_unavailable_generation(self):
        algorithm = genetic_algorithm(self.parameters, self.coordinates)

        self.assertIsNone(algorithm.get_generation(0))
        self.assertIsNone(algorithm.get_generation(-1))


class GeneticAlgorithmEndpointTests(TestCase):
    def test_run_endpoint_exposes_generations_while_run_is_active(self):
        parameters = {
            "bruteForce": False,
            "islands": 3,
            "boats": 6,
            "maxGenerations": 2,
            "mutationRate": 0.1,
            "crossoverRate": 0.8,
            "elitism": 0.1,
            "fitnessFunction": "euclidean",
        }
        islands = {"A": [0, 0], "B": [3, 0], "C": [3, 4]}
        generation_ready = threading.Event()
        continue_run = threading.Event()

        def paused_run(algorithm):
            individual = {"genes": "ABC", "distance": 12}
            with algorithm._record_lock:
                algorithm.generation_record.append({
                    "best": individual,
                    "median": individual,
                    "worst": individual,
                    "all": [individual],
                })
            generation_ready.set()
            continue_run.wait(timeout=2)

        with patch.object(genetic_algorithm, "run", paused_run):
            response = self.client.post(
                "/run/",
                data=json.dumps({"parameters": parameters, "islands": islands}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 202)
            run_id = response.json()["runId"]
            try:
                self.assertTrue(generation_ready.wait(timeout=1))
                result = self.client.get(f"/run/{run_id}/?after=-1").json()
                self.assertEqual(result["status"], "running")
                self.assertEqual(result["generations"][0]["best"]["genes"], "ABC")
            finally:
                continue_run.set()

    def test_run_endpoint_returns_generations_as_they_are_available(self):
        parameters = {
            "bruteForce": False,
            "islands": 3,
            "boats": 6,
            "maxGenerations": 2,
            "mutationRate": 0.1,
            "crossoverRate": 0.8,
            "elitism": 0.1,
            "fitnessFunction": "euclidean",
        }
        islands = {"A": [0, 0], "B": [3, 0], "C": [3, 4]}

        response = self.client.post(
            "/run/",
            data=json.dumps({"parameters": parameters, "islands": islands}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 202)
        run_id = response.json()["runId"]
        status_response = None
        for _ in range(100):
            status_response = self.client.get(f"/run/{run_id}/?after=-1")
            if status_response.json()["status"] != "running":
                break
            time.sleep(0.01)

        self.assertEqual(status_response.status_code, 200)
        result = status_response.json()
        self.assertEqual(result["status"], "completed")
        self.assertEqual([item["number"] for item in result["generations"]], [0, 1])
        self.assertEqual(len(result["generations"][0]["best"]["genes"]), 3)

    def test_run_endpoint_rejects_brute_force_until_implemented(self):
        response = self.client.post(
            "/run/",
            data=json.dumps({
                "parameters": {
                    "bruteForce": True,
                    "islands": 3,
                    "boats": 6,
                    "maxGenerations": 2,
                    "mutationRate": 0.1,
                    "crossoverRate": 0.8,
                    "elitism": 0.1,
                    "fitnessFunction": "euclidean",
                },
                "islands": {"A": [0, 0], "B": [3, 0], "C": [3, 4]},
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("not implemented", response.json()["error"])
