import random

# README: This file acts as a mock genetic algorithm to not hold back development
# To use successfully you must initialise the class and call run() to start the algorithm as it can take some time to run when properly implemented 
# GA = genetic_algorithm.genetic_algorithm(parameters, islands)
# GA.run()
# Then you can call get_generation(generation_number) to get the results of a specific generation
# In a proper implementation you can run
# for i in range(max_generations):
#     GA.get_generation(i)
# To get the results of all the generations even as they are generated

# Given spec kept for implementation of the genetic algorithm in the future.
"""Entry point called by the Run button.

    parameters (dict):
        bruteForce       bool
        islands          int     3-20
        boats            int     1-100
        maxGenerations   int     1-500
        mutationRate     float   0.0-1.0
        crossoverRate    float   0.0-1.0
        elitism          float   0.0-1.0
        fitnessFunction  str     "manhattan" | "euclidean" | "chebyshev"

    islands (dict):
        Island letter -> (x, y) coordinate tuple

        {
            "A": (7, 3),
            "B": (0, 3),
            "C": (12, 8),
            ...
        }

    Returns a dict with the Best, Median and Worst generation values.
    Use None for any value that isn't available.


    # TODO: replace with the real algorithm.
    return {"best": {"genes": "ABCDE"}, 
            "median": {"genes": "ABCDE"}, 
            "worst": {"genes": "ABCDE"}, 
            "all": [
                {"genes": "ABCDE"}, 
                {"genes": "ABCDE"},
                {"genes": "ABCDE"},  
            ]}

"""

class genetic_algorithm:

    def __init__(self, parameters, island_coordinates):
        if parameters["bruteForce"]:
            return # TODO: Not sure how brute force will be implemented yet, so just return for now.

        self.num_nodes = parameters["islands"]
        self.pop_size = parameters["boats"]
        self.max_generations = parameters["maxGenerations"] 
        self.mutation_rate = parameters["mutationRate"]
        self.crossover_rate = parameters["crossoverRate"]
        self.elitism = parameters["elitism"]
        self.fitness_function = parameters["fitnessFunction"] # TODO adjust how fitness function will be selected

        self.island_coordinates = island_coordinates

        self.generation_record = []

    # TODO: Implement run method to execute genetic algorithm
    # Current fills out the generation_record with dummy data for testing purposes
    def run(self):
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:self.num_nodes]

        def make_individual():
            return {"genes": "".join(random.sample(alphabet, self.num_nodes))}

        population = [make_individual() for _ in range(self.pop_size)]
        self.generation_record = [
            {
                "best": population[0],
                "median": population[len(population)//2],
                "worst": population[-1],
                "all": population,
            }
        ]

    def get_generation(self, generation_number):
        if generation_number < 0 or generation_number >= len(self.generation_record):
            return None # TODO make an error maybe
        return self.generation_record[generation_number]