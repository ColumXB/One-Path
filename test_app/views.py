import json

from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.http import require_POST

from . import genetic_algorithm


def landing(request):
    return render(request, "core/landing.html")


@require_POST
def run_algorithm(request):
    """Receive the panel's parameters and island coordinates,
    run the algorithm and return the results as JSON.
    """
    try:
        payload = json.loads(request.body)

        parameters = payload["parameters"]
        islands = payload["islands"]

        # Convert coordinate arrays into Python tuples
        islands = {
            island_id: tuple(coordinates)
            for island_id, coordinates in islands.items()
        }

    except (json.JSONDecodeError, KeyError, TypeError):
        return JsonResponse(
            {"error": "Invalid request data."},
            status=400
        )

    if len(islands) != parameters.get("islands"):
        return JsonResponse(
            {"error": "Island count does not match the number of islands placed."},
            status=400,
        )

    results = genetic_algorithm.run(parameters, islands)

    return JsonResponse(results)