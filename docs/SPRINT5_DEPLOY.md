# Production deployment

The production Compose file uses PostgreSQL 16, a backend with no demo seeding, a built Next.js frontend, and Caddy for HTTPS. It requires a domain whose DNS A/AAAA record points at the host and inbound ports 80 and 443. No public host ports are exposed for PostgreSQL, backend or frontend.

1. Prepare a host with Docker Compose and copy the repository to it. Copy `deploy/production.env.example` to a private environment file outside Git. Set `QOLDAU_DOMAIN`, a unique database password, a matching URL-encoded `QOLDAU_DATABASE_URL`, and `QOLDAU_SECRET_KEY` (generate it with `openssl rand -hex 32`). Keep the file readable only by the deploy account.
2. Run `docker compose --env-file /path/to/qoldau.env -f compose.production.yml up -d --build`. The backend applies Alembic migrations before serving. `QOLDAU_ENVIRONMENT=production` refuses the default secret, SQLite, and non-HTTPS CORS origins.
3. Create the first admin interactively: `docker compose --env-file /path/to/qoldau.env -f compose.production.yml run --rm backend python -m app.bootstrap --email admin@your-domain.example`. This seeds reference units and categories if absent, but creates no demo users or requests. Review unit addresses and routing rules in Configuration before inviting users.
4. Confirm `https://$QOLDAU_DOMAIN/api/ready` returns `{"status":"ready"}` and sign in. `/api/health` checks the process; `/api/ready` also checks database access.

Back up the `pgdata`, `uploads`, `exports`, `models`, and `caddy_data` volumes. A consistent database backup can be made with `docker compose -f compose.production.yml exec -T db pg_dump -U qoldau -Fc qoldau > qoldau.dump`. Test restore into a separate environment before relying on the backup. Keep at least one prior image tag and a verified backup for rollback; schema downgrades should be tested on that backup before use.

The PostgreSQL workflow applies migrations and runs the backend suite on a real PostgreSQL service for each PR. A real deployment still requires the host, domain, DNS, and private values above; this repository does not contain those credentials.
