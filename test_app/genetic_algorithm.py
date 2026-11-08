"""Genetic search for short tours through all islands."""

import math
import random

from .route_search import RouteSearch


class GeneticAlgorithm(RouteSearch):
    """Evolve a population of tours using selection, crossover, and mutation."""

    def __init__(self, parameters, island_coordinates):
        if not isinstance(parameters, dict):
            raise ValueError("Parameters must be an object.")
        if parameters.get("bruteForce") is not False:
            raise ValueError("Genetic algorithm mode requires bruteForce to be false.")

        num_nodes = self._integer_parameter(parameters, "islands", 3, 20)
        self.pop_size = self._integer_parameter(parameters, "boats", 2, 100)
        self.max_generations = self._integer_parameter(
            parameters, "maxGenerations", 1, 500
        )
        self.tournament_size = self._integer_parameter(
            parameters, "tournamentSize", 1, self.pop_size, default=3
        )
        self.mutation_rate = self._rate_parameter(parameters, "mutationRate")
        self.crossover_rate = self._rate_parameter(parameters, "crossoverRate")
        self.elitism = self._rate_parameter(parameters, "elitism")
        self.elite_count = math.floor(self.pop_size * self.elitism)

        super().__init__(parameters, island_coordinates, num_nodes)

    @staticmethod
    def _rate_parameter(parameters, name):
        value = parameters.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a number between 0 and 1.")
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be a number between 0 and 1.")
        return float(value)

    def _evaluate_population(self, population):
        return sorted(
            (
                {"genes": genes, "distance": self.calculate_distance(genes)}
                for genes in population
            ),
            key=lambda individual: individual["distance"],
        )

    def _select_parent(self, ranked_population):
        contestants = random.sample(ranked_population, k=self.tournament_size)
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
        for index, _ in enumerate(route):
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
            self.check_cancelled()
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

    def _search(self):
        population = [
            "".join(random.sample(self.island_ids, self.num_nodes))
            for _ in range(self.pop_size)
        ]

        for generation_number in range(self.max_generations):
            self.check_cancelled()
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


# Preserve the original import name.
genetic_algorithm = GeneticAlgorithm  # pylint: disable=invalid-name
