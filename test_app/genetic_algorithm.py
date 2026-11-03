import math
import random
import threading


class genetic_algorithm:
    def __init__(self, parameters, island_coordinates):
        if not isinstance(parameters, dict):
            raise ValueError("Parameters must be an object.")
        if parameters.get("bruteForce") is not False:
            raise ValueError("Brute-force mode is not implemented.")

        self.num_nodes = self._integer_parameter(parameters, "islands", 3, 20)
        self.pop_size = self._integer_parameter(parameters, "boats", 2, 100)
        self.max_generations = self._integer_parameter(
            parameters, "maxGenerations", 1, 500
        )
        tournament_size = self._integer_parameter(
            parameters, "tournamentSize", 1, self.pop_size, default=3
        )
        self.tournament_size = tournament_size
        self.mutation_rate = self._rate_parameter(parameters, "mutationRate")
        self.crossover_rate = self._rate_parameter(parameters, "crossoverRate")
        self.elitism = self._rate_parameter(parameters, "elitism")
        self.elite_count = math.floor(self.pop_size * self.elitism)

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

    @staticmethod
    def _integer_parameter(parameters, name, minimum, maximum, default=None):
        value = parameters.get(name, default)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer.")
        if not minimum <= value <= maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum}.")
        return value

    @staticmethod
    def _rate_parameter(parameters, name):
        value = parameters.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a number between 0 and 1.")
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be a number between 0 and 1.")
        return float(value)

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
        distance = 0.0
        for index, island_id in enumerate(genes):
            next_island_id = genes[(index + 1) % len(genes)]
            distance += self._pairwise_distances[island_id, next_island_id]
        return distance

    def _evaluate_population(self, population):
        return sorted(
            (
                {"genes": genes, "distance": self.calculate_distance(genes)}
                for genes in population
            ),
            key=lambda individual: individual["distance"],
        )

    def _select_parent(self, ranked_population):
        contestants = random.sample(
            ranked_population, k=self.tournament_size
        )
        return min(contestants, key=lambda individual: individual["distance"])["genes"]

    @staticmethod
    def _ordered_crossover(parent_one, parent_two):
        start, end = sorted(random.sample(range(len(parent_one)), 2))

        def make_child(segment_parent, fill_parent):
            child = [None] * len(segment_parent)
            preserved_segment = segment_parent[start : end + 1]
            child[start : end + 1] = preserved_segment

            remaining_genes = []
            for gene in fill_parent:
                if gene not in preserved_segment:
                    remaining_genes.append(gene)

            # Fill after the preserved segment, wrapping around to the start.
            fill_positions = list(range(end + 1, len(child))) + list(range(start))
            for index, position in enumerate(fill_positions):
                child[position] = remaining_genes[index]

            return "".join(child)

        return (
            make_child(parent_one, parent_two),
            make_child(parent_two, parent_one),
        )

    @staticmethod
    def _mutate(genes, mutation_rate):
        route = list(genes)
        for index in range(len(route)):
            if random.random() < mutation_rate:
                other_positions = [
                    other_index
                    for other_index in range(len(route))
                    if other_index != index
                ]
                other_index = random.choice(other_positions)
                route[index], route[other_index] = (
                    route[other_index],
                    route[index],
                )
        return "".join(route)

    def _next_generation(self, ranked_population):
        next_population = [
            individual["genes"]
            for individual in ranked_population[: self.elite_count]
        ]

        while len(next_population) < self.pop_size:
            parent_one = self._select_parent(ranked_population)
            parent_two = self._select_parent(ranked_population)
            if random.random() < self.crossover_rate:
                children = self._ordered_crossover(parent_one, parent_two)
            else:
                children = (parent_one, parent_two)

            for child in children:
                child = self._mutate(child, self.mutation_rate)
                next_population.append(child)
                if len(next_population) == self.pop_size:
                    break

        return next_population

    def run(self):
        with self._record_lock:
            if self._is_running:
                raise RuntimeError("This genetic algorithm is already running.")
            self._is_running = True
            self.generation_record = []

        try:
            population = [
                "".join(random.sample(self.island_ids, self.num_nodes))
                for _ in range(self.pop_size)
            ]

            for generation_number in range(self.max_generations):
                ranked_population = self._evaluate_population(population)
                generation = {
                    "best": ranked_population[0],
                    "median": ranked_population[len(ranked_population) // 2],
                    "worst": ranked_population[-1],
                    "all": ranked_population,
                }
                with self._record_lock:
                    self.generation_record.append(generation)

                if generation_number + 1 < self.max_generations:
                    population = self._next_generation(ranked_population)
        finally:
            with self._record_lock:
                self._is_running = False

    def get_generation(self, generation_number):
        if isinstance(generation_number, bool) or not isinstance(generation_number, int):
            return None
        with self._record_lock:
            if generation_number < 0 or generation_number >= len(self.generation_record):
                return None
            return self.generation_record[generation_number]

    def get_generations_after(self, generation_number):
        with self._record_lock:
            start = max(generation_number + 1, 0)
            return list(enumerate(self.generation_record[start:], start=start))
