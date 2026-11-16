"""Tests for the run, progress and cancel endpoints."""

import json
import threading
import time
from unittest.mock import patch

from django.test import TestCase

from ..genetic_algorithm import GeneticAlgorithm
from ..route_search import RouteSearch


class AlgorithmEndpointTests(TestCase):
    """Check progress and runtime reporting through the run endpoints."""

    def setUp(self):
        self.islands = {"A": [0, 0], "B": [3, 0], "C": [3, 4]}
        self.parameters = {
            "bruteForce": False,
            "islands": 3,
            "boats": 6,
            "maxGenerations": 2,
            "mutationRate": 0.1,
            "crossoverRate": 0.8,
            "elitism": 0.1,
            "fitnessFunction": "euclidean",
        }

    def start_run(self, parameters):
        """Submit a run and return its ID."""
        response = self.client.post(
            "/run/",
            data=json.dumps({"parameters": parameters, "islands": self.islands}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 202)
        return response.json()["runId"]

    def get_run(self, run_id, after=-1):
        """Fetch and decode a progress response."""
        response = self.client.get(f"/run/{run_id}/", {"after": after})
        self.assertEqual(response.status_code, 200)
        return response.json()

    def wait_for_run(self, run_id):
        """Poll until the worker completes or fails."""
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            result = self.get_run(run_id)
            if result["status"] not in {"running", "cancelling"}:
                return result
            time.sleep(0.01)
        self.fail("Algorithm run did not finish.")

    def test_run_endpoint_exposes_generations_while_run_is_active(self):
        """Return partial progress before the worker reports a runtime."""
        generation_ready = threading.Event()
        continue_run = threading.Event()

        def paused_run(algorithm):
            individual = {"genes": "ABC", "distance": 12}
            # pylint: disable-next=protected-access
            with algorithm._record_lock:
                algorithm.generation_record.append({
                    "best": individual,
                    "median": individual,
                    "worst": individual,
                    "all": [individual],
                })
            generation_ready.set()
            continue_run.wait(timeout=5)

        with patch.object(GeneticAlgorithm, "run", paused_run):
            run_id = self.start_run(self.parameters)
            try:
                self.assertTrue(generation_ready.wait(timeout=2))
                result = self.get_run(run_id)
                self.assertEqual(result["status"], "running")
                self.assertIsNone(result["elapsedMs"])
                self.assertEqual(result["generations"][0]["best"]["genes"], "ABC")
            finally:
                continue_run.set()

        self.assertEqual(self.wait_for_run(run_id)["status"], "completed")

    def test_genetic_run_returns_generations_and_elapsed_time(self):
        """Return numbered generations and timing for a completed genetic run."""
        run_id = self.start_run(self.parameters)

        result = self.wait_for_run(run_id)

        self.assertEqual(result["status"], "completed")
        self.assertGreater(result["elapsedMs"], 0)
        self.assertEqual([item["number"] for item in result["generations"]], [0, 1])
        self.assertEqual(len(result["generations"][0]["best"]["genes"]), 3)
        self.assertEqual(self.get_run(run_id, after=1)["generations"], [])

    def test_brute_force_run_returns_shortest_tour_and_elapsed_time(self):
        """Return the optimum and timing for a completed exhaustive run."""
        run_id = self.start_run({
            "bruteForce": True,
            "islands": 3,
            "fitnessFunction": "euclidean",
        })

        result = self.wait_for_run(run_id)

        self.assertEqual(result["status"], "completed")
        self.assertGreater(result["elapsedMs"], 0)
        self.assertEqual(result["generations"], [{
            "number": 0,
            "best": {"genes": "ABC", "distance": 12},
            "median": None,
            "worst": None,
        }])
        self.assertEqual(self.get_run(run_id, after=0)["generations"], [])

    def test_failed_run_has_no_elapsed_time(self):
        """Return a failure state without reporting a successful runtime."""
        with patch.object(GeneticAlgorithm, "run", side_effect=RuntimeError("test failure")):
            with self.assertLogs("test_app.views", level="ERROR"):
                run_id = self.start_run(self.parameters)
                result = self.wait_for_run(run_id)

        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["elapsedMs"])
        self.assertTrue(result["error"])


    def test_cancel_endpoint_stops_either_solver_even_before_search_starts(self):
        """Cancel an active worker and report a terminal state without a runtime."""
        original_check = RouteSearch.check_cancelled

        for brute_force in (False, True):
            with self.subTest(brute_force=brute_force):
                worker_ready = threading.Event()
                release_worker = threading.Event()

                def paused_check(algorithm, ready=worker_ready, release=release_worker):
                    ready.set()
                    release.wait(timeout=5)
                    original_check(algorithm)

                with patch.object(RouteSearch, "check_cancelled", paused_check):
                    run_id = self.start_run({**self.parameters, "bruteForce": brute_force})
                    try:
                        self.assertTrue(worker_ready.wait(timeout=2))
                        url = f"/run/{run_id}/cancel/"
                        response = self.client.post(url)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.json()["status"], "cancelling")
                        self.assertEqual(self.client.get(url).status_code, 405)
                    finally:
                        release_worker.set()
                    result = self.wait_for_run(run_id)

                self.assertEqual(result["status"], "cancelled")
                self.assertIsNone(result["elapsedMs"])
                self.assertEqual(result["generations"], [])
                self.assertEqual(self.client.post(url).json()["status"], "cancelled")

    def test_cancel_completed_run_preserves_its_result_and_time(self):
        """Keep a finished result when cancellation arrives after computation."""
        run_id = self.start_run(self.parameters)
        result = self.wait_for_run(run_id)

        response = self.client.post(f"/run/{run_id}/cancel/")

        self.assertEqual(response.json()["status"], "completed")
        self.assertEqual(self.get_run(run_id), result)

    def test_cancel_unknown_run_returns_not_found(self):
        """Reject cancellation for an ID that has no worker."""
        response = self.client.post("/run/00000000-0000-0000-0000-000000000000/cancel/")

        self.assertEqual(response.status_code, 404)
