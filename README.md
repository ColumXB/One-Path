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

The site root does not have a page yet; currently, only the admin route is configured. The `test_app` app is an initial placeholder for project code.

## Settings and deployment

The checked-in settings are for local development only. They enable debug mode and use a development-only secret key; do not deploy with these defaults. Production deployments must set `DJANGO_DEBUG=False`, provide a unique `DJANGO_SECRET_KEY`, and set `DJANGO_ALLOWED_HOSTS` to the deployment's hostnames, separated by commas.
