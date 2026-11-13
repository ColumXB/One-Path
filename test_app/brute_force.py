"""Exhaustive search for the shortest tour through all islands."""

from itertools import permutations

from .route_search import RouteSearch

MAX_ISLANDS = 12


class BruteForce(RouteSearch):
    """Find the shortest closed tour and record each improvement."""

    def __init__(self, parameters, island_coordinates):
        if not isinstance(parameters, dict):
            raise ValueError("Parameters must be an object.")

        num_nodes = self._integer_parameter(parameters, "islands", 3, MAX_ISLANDS)
        super().__init__(parameters, island_coordinates, num_nodes)

    def _search(self):
        start, *remaining = self.island_ids
        best_distance = None

        for order in permutations(remaining):
            self.check_cancelled()
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
