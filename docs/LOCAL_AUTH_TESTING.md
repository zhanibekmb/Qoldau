# Local authentication and pilot access

This guide is for a local development database only. Demo credentials are shared and public; never use them on staging or production. The backend's `/api/v1/auth/demo` endpoint is available only when `QOLDAU_ENVIRONMENT=development` and `QOLDAU_DEMO_LOGIN_ENABLED=true`. Production settings reject demo login.

## Start the local demo

From `backend` in PowerShell, use the existing local database. `python -m app.seed` applies migrations and seeds an empty development database; if it already contains the reference data, it reports that it is already seeded. Do not add `--reset` when preserving existing records.

```powershell
$env:QOLDAU_ENVIRONMENT = "development"
$env:QOLDAU_DEMO_LOGIN_ENABLED = "true"
python -m app.seed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If the frontend is on a different origin or the API uses a non-default port, set `QOLDAU_CORS_ORIGINS` before starting the backend and set `NEXT_PUBLIC_API_URL` before starting the frontend. For the standard local ports, open `http://localhost:3000/login`; for the current Qoldau preview, open `http://127.0.0.1:18435/login` (its API is `http://127.0.0.1:18436`). Keep the frontend's `NEXT_PUBLIC_API_URL` pointed at that API.

When the demo endpoint is enabled, the login page displays the sample accounts and shared password. The account directory is non-cacheable and never appears in production. If it is absent locally, check the backend environment and `GET /api/v1/auth/demo`; a `404` means the setting is off or the backend is not in development.

## Seeded sample accounts

The `app.seed` development dataset creates 61 sample accounts: one administrator, 21 agents, nine unit heads, and 30 students. The following representative accounts cover all four roles:

| Role | Sample email | Development password | After login |
|---|---|---|---|
| Student | `student@qoldau.edu.kz` | `Qoldau123!` | `/dashboard` |
| Agent — IT Help Desk | `agent1.it@qoldau.edu.kz` | `Qoldau123!` | `/agent/board` |
| Unit head — Library | `head.library@qoldau.edu.kz` | `Qoldau123!` | `/agent/board` |
| Administrator | `admin@qoldau.edu.kz` | `Qoldau123!` | `/analytics` |

There are sample agents at `agent{1-3}.<unit>@qoldau.edu.kz` where the unit has three agents, `agent{1-2}.<unit>@qoldau.edu.kz` for other units, and unit heads at `head.<unit>@qoldau.edu.kz`. Unit slugs: `deans`, `registrar`, `finance`, `it`, `housing`, `library`, `medical`, `international`, `triage`.

## Local role checks

Sign in with each row above. Confirm the destination shown in the table, open the role's request or work queue, then use **Log out**. Logout clears browser tokens and revokes the current access and refresh tokens on the API. A student must not read another student's request or staff-only endpoints; agents and unit heads are scoped to their unit; only an administrator may manage users, roles, and system configuration. The API enforces these checks even if a user manually enters a URL.

## Creating pilot users

There is no public sign-up. A designated Qoldau administrator creates each pilot user in **Admin → Users** after SDU confirms the participant and their role. Select `student` for a student, `agent` for an employee handling requests, and `unit_head` for the approved head of a service unit. Assign a unit to agents and unit heads. Reserve `admin` for the small, approved system-administrator group.

The administrator issues a unique temporary password and sends it to the verified participant through an SDU-approved separate channel. The user must change it on first sign-in; the temporary password cannot access normal API functions. For a reset, an administrator edits the account and sets a new temporary password. This invalidates existing sessions and forces the next sign-in to change the password. Deactivating an account also invalidates its sessions. The current system does not provide self-service password recovery or send account invitations/reset links.

For the first production administrator only, use the interactive bootstrap command in [SPRINT5_DEPLOY.md](SPRINT5_DEPLOY.md). It requires a unique password of at least 12 characters and creates no demo users or sample requests. Review the units and routing configuration before inviting pilot users. Do not run `app.seed` in production.

## SSO status

Qoldau currently uses its own email/password authentication with bcrypt password hashes and signed access/refresh tokens. University SSO (SAML/OIDC) is not implemented or configured. Do not imply that a Qoldau account is an SDU identity-provider account; pilot role approval and account lifecycle remain administrator-managed.
