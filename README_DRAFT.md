# One-Path

An interactive web visualiser that compares a genetic algorithm against a brute-force method on the shortest closed tour through a set of islands, solving the traveling salesman problem.

- **Live site:** https://one-path.onrender.com/

---

## 1. Selected algorithm

| | |
|---|---|
| **Main algorithm** | Genetic algorithm (tournament selection, ordered crossover, swap mutation, elitism) |
| **Baseline** | Brute-force exhaustive search (used to verify the genetic algorithm's answer and to compare run time) |

## 2. Problem

One-Path solves the **Travelling Salesman Problem (TSP)**. Given *n* islands placed on a 50 × 30 grid, find the shortest route that visits every island exactly once and returns to the starting island.

- A route is a string of island IDs, e.g. `"ACBDE"`. The return leg from the last island back to the first is included in the distance.
- Distance can be measured with the **Manhattan**, **Euclidean** or **Chebyshev** metric.
- TSP is NP-hard: the number of possible tours grows factorially, so exact search quickly becomes impractical. A genetic algorithm trades a guarantee of optimality for a fast, usually near-optimal answer.

## 3. Intended users

- Students learning about the TSP, heuristics and genetic algorithms.
- Educators who want to demonstrate visually how GA parameters (population, mutation, crossover, elitism, tournament size) affect convergence.
- Anyone who wants to see the gap between exact and heuristic search as the number of islands grows.

---

## 4. Installation, access and testing

### Requirements

- Python 3.13 or newer (the project was developed and deployed on 3.14)
- Git
- A modern web browser

### Install

```sh
git clone https://github.com/ColumXB/One-Path.git
cd One-Path

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
python manage.py migrate
```

### Run and access

```sh
python manage.py runserver
```

Open <http://127.0.0.1:8000/> in a browser.

1. Click cells on the grid to place islands (the island count slider sets how many).
2. Choose a fitness (distance) function.
3. Toggle **Brute Force** on for exhaustive search, or leave it off and tune the genetic algorithm sliders.
4. Press **Run**. Progress streams in as it is computed; press **Cancel** to stop a run.
5. The side panel shows the best / median / worst route (genetic) or the best route found (brute force), plus run time for each algorithm.

### Run the tests

```sh
python manage.py test
```

### Settings for deployment

Local defaults enable debug mode. In production set `DJANGO_DEBUG=False`, a unique `DJANGO_SECRET_KEY`, and `DJANGO_ALLOWED_HOSTS`. `render.yaml` contains the configuration used for hosting on Render (gunicorn + WhiteNoise).

### Interface parameters

| Parameter | Range | Default | Notes |
|---|---|---|---|
| Islands | 3 – 20 (3 – 12 for brute force) | 5 | |
| Boats (population size) | 2 – 100 | 10 | Greyed out in brute-force mode |
| Tournament size | 1 – population size | 3 | |
| Generations | 1 – 500 | 50 | |
| Mutation rate | 0 – 100 % | 5 % | |
| Crossover rate | 0 – 100 % | 75 % | |
| Elitism | 0 – 100 % | 10 % | Fraction of population copied unchanged |

### HTTP API (used by the front end)

| Method | Path | Purpose |
|---|---|---|
| POST | `/run/` | Validate input, start a background run, return `runId` |
| GET | `/run/<id>/?after=<n>` | Poll status and any generations after index `n` |
| POST | `/run/<id>/cancel/` | Request cancellation |

---

## 5. Algorithm explanation

Let *n* = number of islands, *P* = population size ("boats"), *G* = number of generations, *k* = tournament size.

Shared set-up (`route_search.py`): all pairwise distances are computed once and cached, so scoring a tour is *n* table look-ups.

### 5.1 Genetic algorithm (`genetic_algorithm.py`)

```
population ← P random permutations of the islands
for generation in 1 … G:
    rank population by tour distance (shortest first)
    record best, median, worst
    if not last generation:
        next ← the top floor(P × elitism) tours          # elitism
        while len(next) < P:
            p1 ← best of k random tours                  # tournament selection
            p2 ← best of k random tours
            if random() < crossoverRate:
                c1, c2 ← ordered_crossover(p1, p2)       # keep a slice of one parent,
            else:                                        # fill the rest in the other
                c1, c2 ← p1, p2                          # parent's order
            for each child:
                for each position i:                     # swap mutation
                    if random() < mutationRate: swap gene i with a random other gene
                add child to next
        population ← next
```

Every operator keeps each island exactly once, so every individual is always a valid tour.

### 5.2 Brute force (`brute_force.py`)

```
fix island A as the start                         # removes rotated duplicates
best ← ∞
for each permutation of the remaining n-1 islands:
    skip if first > last                          # removes mirror-image (reversed) tours
    d ← tour distance
    if d < best: best ← d; record the improvement
```

This evaluates (n−1)!/2 distinct tours and is guaranteed to return the optimal tour.

### 5.3 Complexity

| | Time | Space |
|---|---|---|
| **Brute force** | O((n−1)! · n): (n−1)! permutations are generated, half are skipped, and each remaining tour costs O(n) to score | O(n²) for the distance cache, plus O(n) per recorded improvement |
| **Genetic algorithm** | O(G · P · (n² + k + log P)) | O(n² + G · P · n) |

Notes on the genetic algorithm figures:

- Per generation: scoring is O(P·n), sorting is O(P log P), and breeding costs O(k) per selection plus O(n²) per crossover (membership check against the preserved slice) and O(n) per mutation pass, repeated P times.
- Space: the distance cache is O(n²); the live population is O(P·n). The implementation also stores the full ranked population for **every** generation so the front end can animate it, which is the dominant term, O(G·P·n).
- For a fixed budget (*G*, *P*) the genetic algorithm is **polynomial** in *n*, whereas brute force is **factorial**. That is why brute force is capped at 12 islands.

---

## 6. Test cases and results

### 6.1 Automated tests

25 tests in `test_app/tests.py`, all run with `python manage.py test`.

| Group | What is checked |
|---|---|
| Admin page | Django admin login page responds (smoke test) |
| Genetic algorithm | Every generation has *P* valid tours (right length, each island once, non-negative distance); best ≤ median ≤ worst; closed-tour distance including the return leg for Manhattan (14), Euclidean (12) and Chebyshev (11) on a 3-4-5 triangle; symmetric distance cache with no self-legs |
| GA parameter validation | Population < 2 rejected; tournament size > population rejected; tournament size read from parameters |
| GA operators | Ordered crossover and swap mutation always return each island exactly once; mutation is evaluated per gene and can make several swaps in one pass; a 0 % mutation rate leaves the tour unchanged; out-of-range generation lookups return `None` |
| Brute force | On a 4-island rectangle the recorded improvements are exactly ABCD = 18 → ABDC = 16 → ACBD = 14 (the known optimum); boat count is ignored and re-running resets progress; 13 islands rejected; 12 islands accepted |
| Cancellation | Cancelling before start is honoured and the solver can be run again; both solvers stop mid-search and keep the progress already recorded |
| HTTP endpoints | Partial progress is visible while a run is active; completed genetic and brute-force runs return generations and elapsed time; a crashed worker reports `failed` with no run time; cancel reports `cancelling` then `cancelled`; cancelling a finished run keeps its result; unknown run ID returns 404; GET on the cancel URL returns 405 |

**Result:** 25 / 25 tests pass (`Ran 25 tests … OK`).

### 6.2 Genetic algorithm vs brute force

Measured with Euclidean distance, random island positions on a 30 × 20 grid, and the genetic algorithm set to 50 boats, 200 generations, 5 % mutation, 75 % crossover, 10 % elitism and tournament size 3. The GA was run 10 times on each map. Timings are from one development machine, so treat them as indicative only.

| Islands | Brute force time | Brute force best | GA time (per run) | GA runs matching the optimum |
|---|---|---|---|---|
| 8 | ≈ 0.002 s | 68.31 | ≈ 0.03 s | 10 / 10 |
| 10 | ≈ 0.19 s | 73.13 | ≈ 0.04 s | 10 / 10 |
| 11 | ≈ 2.1 s | 81.52 | ≈ 0.04 s | 10 / 10 |
| 20 (GA only) | not feasible | n/a | ≈ 0.3 s (100 boats, 500 generations) | best distance fell from 204.3 (generation 0) to 89.6 |

**Summary:** Brute force time grows roughly 10× per extra island at this size, matching the factorial bound, while GA time stays almost flat. On every map where the optimum could be computed, the genetic algorithm found it in all 10 runs. At 20 islands, where brute force cannot run, the GA still reduced the best tour length by more than half over its run.

<!-- TODO (team): add screenshots or your own timing/accuracy runs if you have them. -->

---

## 7. Known limitations, dependencies and third-party resources

### Known limitations

- **Brute force is capped at 12 islands**; beyond that the factorial run time is impractical. The island slider goes to 20 for the genetic algorithm only.
- The genetic algorithm is a **heuristic**: it does not guarantee the optimal tour, and results vary run to run (it is not seeded).
- **Run state is held in server memory** (a Python dictionary guarded by a lock). Runs are lost on restart, are never cleaned up, and are not shared between multiple gunicorn workers.
- Runs execute on **background threads** inside the web process, with no queue or limit on concurrent runs, so heavy use could slow the server.
- The server stores every individual of every generation, so memory use grows with *G* × *P* × *n*.
- Cancellation is cooperative: it takes effect at the next check, not instantly.
- Only symmetric distance metrics on a grid of whole cells are supported; there are no obstacles, real-world distances or fixed start points.
- Island IDs are the letters A–T, which is what limits the map to 20 islands.
- The Django database is unused apart from the built-in admin and auth tables.
- Hosted on a free Render plan, so the live site may be slow to wake up.

### Dependencies (`requirements.txt`)

| Package | Version | Purpose |
|---|---|---|
| Django | 6.1.2 | Web framework, routing, tests |
| asgiref | 3.13.0 | Django dependency |
| sqlparse | 0.6.0 | Django dependency |
| tzdata | 2026.5 | Time zone data |
| gunicorn | 23.0.0 | Production WSGI server |
| whitenoise | 6.9.0 | Serves static files in production |

The algorithms themselves use only the Python standard library (`random`, `itertools`, `math`, `threading`). The front end is plain HTML, CSS and JavaScript with no external libraries.

### Third-party resources

- Hosting: [Render](https://render.com/)
- <!-- TODO (team): list any fonts, icons, images, tutorials, papers or code references you used. Cite the source of the ordered crossover (OX) and tournament selection descriptions if taken from a paper or lecture notes. -->

### Licence

MIT. See `LICENSE`.

---

## 8. Team contributions

<!-- TODO: each member to fill in their own section. Be specific (files, features, tests, documentation) and keep it factual. -->

| Member | Student ID | Contributions |
|---|---|---|
| FinnGos | <!-- ID --> | <!-- e.g. hosting and deployment, ... --> |
| ColumXB | <!-- ID --> | <!-- e.g. brute-force baseline, ... --> |
| <!-- Name --> | <!-- ID --> | <!-- Contributions --> |
| <!-- Name --> | <!-- ID --> | <!-- Contributions --> |

## 9. Acknowledgement of generative AI use

<!-- TODO: each member to complete and confirm accuracy. Follow the module's required wording/format for AI declarations. -->

| Member | Tool and version | What it was used for | How the output was checked or modified |
|---|---|---|---|
| <!-- Name --> | <!-- e.g. Claude Code (Sonnet 5.5) --> | <!-- e.g. drafting this README, code review --> | <!-- e.g. reviewed and edited by hand --> |
| <!-- Name --> | <!-- Tool --> | <!-- Use --> | <!-- Verification --> |
| <!-- Name --> | <!-- Tool --> | <!-- Use --> | <!-- Verification --> |

> This README draft was generated with the assistance of Claude Code (Sonnet 5.5) from the project source code and then reviewed by the team. <!-- TODO: confirm and adjust. -->
