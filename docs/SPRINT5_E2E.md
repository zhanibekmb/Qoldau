# Sprint 5 browser scenarios

Playwright covers five connected flows in Chromium: student submission and messaging, agent status change and reply, admin FAQ publication, configuration keyword creation and removal, and analytics export with a valid download. The tests use the existing demo accounts and create records with unique names. CI resets an isolated SQLite database; it never touches production data.

To run locally, start the backend with an isolated database and a seeded demo dataset, then start the frontend and run Playwright:

```bash
export QOLDAU_DATABASE_URL=sqlite:////tmp/qoldau-sprint5-e2e.db
export QOLDAU_SCHEDULER_ENABLED=false QOLDAU_JOBS_INLINE=true
export QOLDAU_UPLOAD_DIR=/tmp/qoldau-sprint5-e2e-uploads
export QOLDAU_EXPORT_DIR=/tmp/qoldau-sprint5-e2e-exports
cd backend
python -m app.seed --reset --demo
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
cd frontend
npm ci
npx playwright install chromium
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run build
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run start
```

In a third terminal, run `cd frontend && npm run test:e2e`. The CI workflow in `.github/workflows/e2e.yml` runs the same scenarios on pull requests.
