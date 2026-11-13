"""Shared route validation, scoring, and progress tracking."""

import math
import threading
from abc import ABC, abstractmethod


class SearchCancelled(Exception):
    """Signal that the current search was cancelled."""


class RouteSearch(ABC):
    """Shared route scoring and thread-safe progress for both solvers."""

    def __init__(self, parameters, island_coordinates, num_nodes):
        self.num_nodes = num_nodes
        self.fitness_function = parameters.get("fitnessFunction")
        if not isinstance(self.fitness_function, str) or self.fitness_function not in {
            "manhattan",
            "euclidean",
            "chebyshev",
        }:
            raise ValueError("Fitness function must be manhattan, euclidean, or chebyshev.")

        self.island_coordinates = self._validated_coordinates(island_coordinates)
        self.island_ids = tuple(sorted(self.island_coordinates))
        expected_ids = tuple(chr(ord("A") + index) for index in range(self.num_nodes))
        if self.island_ids != expected_ids:
            raise ValueError("Island IDs must be consecutive uppercase letters starting at A.")

        self._pairwise_distances = self._calculate_pairwise_distances()
        self.generation_record = []
        self._record_lock = threading.Lock()
        self._is_running = False
        self._cancel_event = threading.Event()

    @staticmethod
    def _integer_parameter(parameters, name, minimum, maximum, default=None):
        value = parameters.get(name, default)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer.")
        if not minimum <= value <= maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum}.")
        return value

    def _validated_coordinates(self, coordinates):
        if not isinstance(coordinates, dict) or len(coordinates) != self.num_nodes:
            raise ValueError("Island coordinates must match the island count.")

        validated = {}
        for island_id, point in coordinates.items():
            if not isinstance(island_id, str) or len(island_id) != 1:
                raise ValueError("Island IDs must be single uppercase letters.")
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                raise ValueError(f"Coordinates for island {island_id} must contain x and y.")
            if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in point
            ):
                raise ValueError(f"Coordinates for island {island_id} must be finite numbers.")
            validated[island_id] = (float(point[0]), float(point[1]))
        return validated

    def _calculate_pairwise_distances(self):
        distances = {}
        for index, island_id in enumerate(self.island_ids):
            x1, y1 = self.island_coordinates[island_id]
            for other_id in self.island_ids[index + 1 :]:
                x2, y2 = self.island_coordinates[other_id]
                dx = abs(x1 - x2)
                dy = abs(y1 - y2)

                if self.fitness_function == "manhattan":
                    distance = dx + dy
                elif self.fitness_function == "chebyshev":
                    distance = max(dx, dy)
                else:
                    distance = math.hypot(dx, dy)

                distances[island_id, other_id] = distance
                distances[other_id, island_id] = distance
        return distances

    def calculate_distance(self, genes):
        """Return the total distance of a tour, including its return leg."""
        distance = 0.0
        for index, island_id in enumerate(genes):
            next_island_id = genes[(index + 1) % len(genes)]
            distance += self._pairwise_distances[island_id, next_island_id]
        return distance

    def run(self):
        """Reset progress and execute the solver with a guard against concurrent runs."""
        with self._record_lock:
            if self._is_running:
                raise RuntimeError("This algorithm is already running.")
            self._is_running = True
            self.generation_record = []

        try:
            self.check_cancelled()
            self._search()
            self.check_cancelled()
        finally:
            with self._record_lock:
                self._is_running = False
                self._cancel_event.clear()

    def cancel(self):
        """Request that the current search stop at its next cancellation check."""
        self._cancel_event.set()

    def check_cancelled(self):
        """Stop the search when cancellation has been requested."""
        if self._cancel_event.is_set():
            raise SearchCancelled()

    @abstractmethod
    def _search(self):
        """Perform the search and record its progress."""

    def get_generation(self, generation_number):
        """Return the requested progress record if it is available."""
        if isinstance(generation_number, bool) or not isinstance(generation_number, int):
            return None
        with self._record_lock:
            if generation_number < 0 or generation_number >= len(self.generation_record):
                return None
            return self.generation_record[generation_number]

    def get_generations_after(self, generation_number):
        """Return numbered progress records after the supplied index."""
        with self._record_lock:
            start = max(generation_number + 1, 0)
            return list(enumerate(self.generation_record[start:], start=start))
