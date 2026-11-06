import math
import threading
from itertools import permutations


MAX_ISLANDS = 10
DISTANCE_FUNCTIONS = {
    "manhattan": lambda dx, dy: dx + dy,
    "euclidean": math.hypot,
    "chebyshev": max,
}


class brute_force:
    """Find the shortest closed tour and record each improvement."""

    def __init__(self, parameters, island_coordinates):
        if not isinstance(parameters, dict):
            raise ValueError("Parameters must be an object.")

        self.num_nodes = parameters.get("islands")
        if isinstance(self.num_nodes, bool) or not isinstance(self.num_nodes, int):
            raise ValueError("islands must be an integer.")
        if not 3 <= self.num_nodes <= MAX_ISLANDS:
            raise ValueError(f"For brute force, islands must be between 3 and {MAX_ISLANDS}.")

        self.fitness_function = parameters.get("fitnessFunction")
        if not isinstance(self.fitness_function, str) or self.fitness_function not in DISTANCE_FUNCTIONS:
            raise ValueError("Fitness function must be manhattan, euclidean, or chebyshev.")

        self.island_ids = tuple(chr(ord("A") + index) for index in range(self.num_nodes))
        self.island_coordinates = self._validated_coordinates(island_coordinates)
        self._pairwise_distances = self._calculate_pairwise_distances()
        self.generation_record = []
        self._record_lock = threading.Lock()
        self._is_running = False

    def _validated_coordinates(self, coordinates):
        if not isinstance(coordinates, dict) or len(coordinates) != self.num_nodes:
            raise ValueError("Island coordinates must match the island count.")
        if set(coordinates) != set(self.island_ids):
            raise ValueError("Island IDs must be consecutive uppercase letters starting at A.")

        validated = {}
        for island_id, point in coordinates.items():
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
        metric = DISTANCE_FUNCTIONS[self.fitness_function]
        distances = {}
        for index, island_id in enumerate(self.island_ids):
            x1, y1 = self.island_coordinates[island_id]
            for other_id in self.island_ids[index + 1:]:
                x2, y2 = self.island_coordinates[other_id]
                distance = metric(abs(x1 - x2), abs(y1 - y2))
                distances[island_id, other_id] = distance
                distances[other_id, island_id] = distance
        return distances

    def calculate_distance(self, genes):
        distance = 0.0
        for index, island_id in enumerate(genes):
            next_island_id = genes[(index + 1) % len(genes)]
            distance += self._pairwise_distances[island_id, next_island_id]
        return distance

    def run(self):
        with self._record_lock:
            if self._is_running:
                raise RuntimeError("This brute-force search is already running.")
            self._is_running = True
            self.generation_record = []

        try:
            self._search()
        finally:
            with self._record_lock:
                self._is_running = False

    def _search(self):
        start, *remaining = self.island_ids
        best_distance = None

        for order in permutations(remaining):
            # Starting at A removes rotated duplicates. Skip reverse tours too.
            if order[0] > order[-1]:
                continue

            genes = start + "".join(order)
            distance = self.calculate_distance(genes)
            if best_distance is None or distance < best_distance:
                best_distance = distance
                with self._record_lock:
                    self.generation_record.append({
                        "best": {"genes": genes, "distance": distance},
                        "median": None,
                        "worst": None,
                    })

    def get_generation(self, generation_number):
        if isinstance(generation_number, bool) or not isinstance(generation_number, int):
            return None
        with self._record_lock:
            if 0 <= generation_number < len(self.generation_record):
                return self.generation_record[generation_number]
            return None

    def get_generations_after(self, generation_number):
        with self._record_lock:
            start = max(generation_number + 1, 0)
            return list(enumerate(self.generation_record[start:], start=start))
