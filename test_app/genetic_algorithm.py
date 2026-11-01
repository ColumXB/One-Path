def run(parameters, islands):
    """Entry point called by the Run button.

    parameters (dict):
        bruteForce       bool
        islands          int     3-20
        boats            int     1-100
        populationSize   int     5-500
        nodes            int     2-10
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
    """

    # TODO: replace with the real algorithm.
    return {"best": None, "median": None, "worst": None}