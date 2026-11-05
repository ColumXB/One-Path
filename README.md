# One-Path

## Getting started

You need Python 3.13 and Git. Clone the repository and move into the project folder:

```sh
git clone https://github.com/ColumXB/One-Path.git
cd One-Path
```

Create a virtual environment using the command for your operating system:

**Windows (PowerShell):**

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If `py -3.13` is not available, install Python 3.13 first. On Windows systems using the Python Install Manager, run `pymanager install 3.13`.

**Windows (Command Prompt):**

```bat
py -3.13 -m venv .venv
.venv\Scripts\activate.bat
```

**macOS/Linux:**

```sh
python3.13 -m venv .venv
source .venv/bin/activate
```

With the virtual environment active, install the pinned dependencies, prepare the local database, and start the development server:

```sh
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) to see the Django admin. To sign in, create your own local admin account:

```sh
python manage.py createsuperuser
```

Run the automated checks with:

```sh
python manage.py test
```

In VS Code, select the project's `.venv` interpreter (`.venv\Scripts\python.exe` on Windows or `.venv/bin/python` on macOS/Linux). Stop the server with **Ctrl+C**.

The site root provides the One-Path island map and genetic algorithm controls. A run uses a permutation of the island IDs as its route; the return leg from the last island to the first is included in its distance. The algorithm minimizes the selected Manhattan, Euclidean, or Chebyshev distance and uses tournament selection, ordered crossover, per-island swap mutation, and elitism. The mutation rate is checked independently for each island in a child route; selected islands swap positions with another island. The population size must be from 2 to 100. Tournament size must be from 1 to the population size and defaults to 3; its frontend control updates its maximum as population size changes.

Ten evenly spaced generations are demonstrated on the map with one coloured boat dot per route, always including the first and last generation (runs shorter than ten generations demonstrate every generation). Demonstration routes are rotated so every boat starts and returns at island A, and the route lines are hidden while the boats move. When the run finishes, the best, median, and worst routes are shown as separate overlays. Each of those final routes can be toggled on or off with the controls in the Last run section.

Runs execute in a background thread in the Django process, and the page polls for newly completed generations. This is a prototype implementation: run history is held in process memory, so it is lost on restart and is not shared across multiple server workers. Brute-force mode is not implemented yet.

## Settings and deployment

The checked-in settings are for local development only. They enable debug mode and use a development-only secret key; do not deploy with these defaults. Production deployments must set `DJANGO_DEBUG=False`, provide a unique `DJANGO_SECRET_KEY`, and set `DJANGO_ALLOWED_HOSTS` to the deployment's hostnames, separated by commas.
