# Backend

FastAPI service for the Library System.

## Configure a secret key

`SECRET_KEY` is required at application startup. The service refuses to start when it is missing, blank, or set to the insecure development placeholder `development-only-secret-key-change-me`.

Generate a cryptographically random key in PowerShell and keep it in the current shell session:

```powershell
$env:SECRET_KEY = (& .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))").Trim()
```

Alternatively, place the generated value in a local, untracked `.env` at the repository root:

```dotenv
SECRET_KEY=<paste-a-new-random-value-here>
```

Never commit a real secret or paste one into source files, tests, or documentation.

## Run locally

From the repository root, apply migrations and start the API:

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive documentation is at `/docs`.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest
```

When running tests in a fresh shell, provide a non-production test key first, for example:

```powershell
$env:SECRET_KEY = "local-test-only-$(Get-Random)"
```
