# FastAPI Auth Boilerplate

A starter FastAPI backend with email/password signup, OTP verification (email or
SMS), Google OAuth login, password reset, and JWT-protected routes.

## Create Virtual Environment

```bash
python -m venv .venv
```

## Activate Virtual Enviroment

Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

OR in Mac/Linux:

```bash
source .venv/bin/activate
```

## Install Requirements

```bash
pip install -r requirements.txt
```

## Environment Setup

Copy the example file and fill in your values:

```powershell
Copy-Item .env.example .env
```

OR in Mac/Linux:

```bash
cp .env.example .env
```

`DATABASE_URL`, `SECRET_KEY`, and `ENCRYPTION_KEY` are required — the app will
refuse to start without them. Everything else is only needed for the feature it
belongs to (SMTP for email OTPs and password reset, Google keys for OAuth, AWS
keys for SMS OTPs).

To generate the two secrets:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

`ENCRYPTION_KEY` must stay fixed once you have live users. It encrypts the user
IDs handed out during signup, so changing it invalidates any OTP flow already in
progress.

`CORS_ORIGINS` is a comma-separated list of browser origins allowed to call the
API. It cannot be `*` because the API sends credentials, so add your real
frontend origin before deploying.

### Password reset page

Reset emails link to `PASSWORD_RESET_URL` with the token appended as
`?token=<uuid>`. By default this points at a plain reset page the API serves
itself at `/auth/reset-password`, so the flow works end to end without a
frontend. The page collects the new password and posts it back to the JSON API.

When you build your own page, point `PASSWORD_RESET_URL` at it and have it read
the `token` query parameter and `POST` to `/auth/reset-password` with
`{token, new_password, confirm_password}`. Tokens last 15 minutes and work once.

### Database (Neon)

1. Create a project at [console.neon.tech](https://console.neon.tech).
2. Open **Connect** and copy the **Pooled connection** string.
3. Paste it into `DATABASE_URL` in `.env`.
4. If it starts with `postgres://`, change it to `postgresql://` — SQLAlchemy
  requires the longer form.
5. Keep `?sslmode=require` on the end; Neon rejects unencrypted connections.

Tables are created automatically on first startup, so there is no migration step
to run.

## Run Command

```bash
uvicorn app.main:app --reload
```

OR run the following to specify port number and to allow all host:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive API docs are then at [http://localhost:8000/docs](http://localhost:8000/docs).