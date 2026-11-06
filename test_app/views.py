import json
import logging
import threading
import uuid
from time import perf_counter

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from . import brute_force, genetic_algorithm

logger = logging.getLogger(__name__)
_runs = {}
_runs_lock = threading.Lock()


def landing(request):
    return render(request, "core/landing.html")


def _execute_run(run_id, algorithm):
    started_at = perf_counter()
    try:
        algorithm.run()
    except Exception:
        logger.exception("Algorithm run %s failed.", run_id)
        with _runs_lock:
            _runs[run_id]["status"] = "failed"
            _runs[run_id]["error"] = "The algorithm failed. Check the server logs."
    else:
        elapsed_ms = (perf_counter() - started_at) * 1000
        with _runs_lock:
            _runs[run_id]["elapsedMs"] = elapsed_ms
            _runs[run_id]["status"] = "completed"


@require_POST
def run_algorithm(request):
    """Start an algorithm run and return its ID for progress polling."""
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request data."}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({"error": "Request data must be an object."}, status=400)

    parameters = payload.get("parameters")
    islands = payload.get("islands")
    if not isinstance(parameters, dict) or not isinstance(islands, dict):
        return JsonResponse(
            {"error": "Parameters and island coordinates are required."}, status=400
        )

    brute_force_enabled = parameters.get("bruteForce")
    if not isinstance(brute_force_enabled, bool):
        return JsonResponse({"error": "bruteForce must be a boolean."}, status=400)

    if len(islands) != parameters.get("islands"):
        return JsonResponse(
            {"error": "Island count does not match the number of islands placed."},
            status=400,
        )

    try:
        algorithm_class = (
            brute_force.brute_force if brute_force_enabled else genetic_algorithm.genetic_algorithm
        )
        algorithm = algorithm_class(parameters, islands)
    except (TypeError, ValueError) as error:
        return JsonResponse({"error": str(error)}, status=400)

    run_id = uuid.uuid4()
    with _runs_lock:
        _runs[str(run_id)] = {
            "algorithm": algorithm,
            "status": "running",
            "error": None,
            "elapsedMs": None,
        }

    worker = threading.Thread(
        target=_execute_run,
        args=(str(run_id), algorithm),
        daemon=True,
    )
    try:
        worker.start()
    except RuntimeError:
        logger.exception("Could not start algorithm run %s.", run_id)
        with _runs_lock:
            _runs.pop(str(run_id), None)
        return JsonResponse({"error": "Could not start the algorithm run."}, status=503)

    return JsonResponse({"runId": run_id, "status": "running"}, status=202)


@require_GET
def get_run(request, run_id):
    try:
        after = int(request.GET.get("after", "-1"))
    except ValueError:
        return JsonResponse({"error": "The after value must be an integer."}, status=400)
    if after < -1:
        return JsonResponse({"error": "The after value cannot be less than -1."}, status=400)

    with _runs_lock:
        run = _runs.get(str(run_id))
        if run is None:
            return JsonResponse({"error": "Run not found."}, status=404)
        status = run["status"]
        error = run["error"]
        elapsed_ms = run["elapsedMs"]
        algorithm = run["algorithm"]

    generations = [
        {"number": number, **generation}
        for number, generation in algorithm.get_generations_after(after)
    ]
    return JsonResponse(
        {
            "runId": str(run_id),
            "status": status,
            "generations": generations,
            "error": error,
            "elapsedMs": elapsed_ms,
        }
    )
