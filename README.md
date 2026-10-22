<p align="center"><img src="frontend/public/logo.svg" width="96" alt="Qoldau logo"></p>

# Qoldau — AI Student Request Routing & Support System (SDU University)

Students submit any request in free text (Kazakh, Russian or English). The system detects the category and
urgency, routes the request to the responsible university unit and agent, tracks it with SLA timers through a
defined workflow, and reports on it in an analytics dashboard.

This repository implements **Sprints 1–4 (US1–US22)** from `Sprint.xlsx`. Sprint 4 added report export, AI
retraining with model management, smart replies for agents, FAQ / similar-request suggestions for students and a
knowledge base (see `docs/SPRINT4_PLAN.md`, `docs/SPRINT4_CHANGELOG.md`, `docs/SPRINT4_DEMO.md`). Sprint 5 items
(full RBAC audit, rate limiting, E2E suite, production deployment) are not built yet.

## Brand & landing page

- **Logo:** a mortarboard (the student), an S-shaped route (it follows the path to the right office, and S stands for SDU), and a chat bubble (the conversation). See `frontend/components/Logo.tsx`, `frontend/app/icon.svg` (favicon) and `frontend/public/logo.svg`.
- **UI:** plain and flat. One action colour (SDU blue `#1B45B4`), neutral greys, no gradients, glows or decorative shadows. Status colours are used only for status. The navy/teal/amber logo colours stay in the logo. Light and dark tokens live in `app/globals.css`.
- **Type:** Inter only, with Kazakh Cyrillic support.
- **Landing (`/`):** a headline with one button and a real routing example you can click through, then how it works, the offices, response times (SLA), FAQ and a closing call to action. It's fully translated (KZ/RU/EN), has light/dark themes and 44px touch targets.
- **Design skills:** 8 skills from [affaan-m/ecc](https://github.com/affaan-m/ecc) are installed per project in `.claude/skills`: frontend-design-direction, design-system, accessibility, frontend-a11y, motion-foundations, motion-patterns, nextjs-turbopack and seo.

## Quick start (local, no Docker)

Requirements: Python 3.12+ and Node 20+.

```bash
# Backend: http://localhost:8000  (API docs at /api/docs)
cd backend
pip install -r requirements.txt
python -m app.seed            # migrations + 9 units, 61 users, 520+ requests, knowledge base (--reset to rebuild)
# python -m app.seed --reset --demo   # Sprint 4 Review data (model versions v1.1/v1.2 + 260 new labels); or: make demo
uvicorn app.main:app --port 8000

# Frontend: http://localhost:3000
cd frontend
npm install
npm run dev
```

Demo accounts (password `Qoldau123!`):

| Role | Email |
|---|---|
| Student (owns REQ-2026-00123) | `student@qoldau.edu.kz` |
| Agent — IT Help Desk | `agent1.it@qoldau.edu.kz` (any unit: `agent{1-3}.<unit>@qoldau.edu.kz`) |
| Agent — Triage queue | `agent1.triage@qoldau.edu.kz` |
| Unit head — Library | `head.library@qoldau.edu.kz` (`head.<unit>@…`) |
| Admin | `admin@qoldau.edu.kz` |

Unit slugs: `deans, registrar, finance, it, housing, library, medical, international, triage`.

An existing Sprints 1–3 database is upgraded in place: `python -m app.seed` runs migration 0002 and adds the
knowledge base without touching existing requests.

**Docker:** `docker compose up --build` starts PostgreSQL, the API (it migrates and seeds on first start) and the web app.

## Tests and model evaluation

```bash
cd backend && python -m pytest -q          # 58 tests mapped to the USxQATest Given/When/Then scenarios
python -m app.ml.evaluate                  # accuracy / macro F1 / routing correctness -> docs/model-evaluation.md
python -m app.ml.training [--force]        # retrain from agent feedback (same as "Retrain now")
python -m app.ml.embeddings --reindex      # rebuild the FAQ / template / resolved-case vector index
cd frontend && npx tsc --noEmit && npm run lint && npm run build
```

GitHub Actions (`.github/workflows/ci.yml`) runs all of these.

## Architecture

```
frontend/ (Next.js 16, React 19, Tailwind 4, Recharts, dnd-kit)
  app/login, app/(app)/{dashboard, requests, requests/new, requests/[id], agent/board, agent/triage,
                        agent/requests, analytics, admin, admin/models, kb, reports, notifications}
  lib/{api, auth, i18n (KZ/RU/EN), realtime (WebSocket), theme (light/dark)}

backend/ (FastAPI, SQLAlchemy 2, Alembic, scikit-learn, APScheduler)
  app/api/       auth, requests, ai (+model management), suggestions, kb, export, messages (+attachments, CSAT,
                 notifications), analytics, admin, meta, ws
  app/services/  pipeline (submit -> classify -> prioritise -> route -> SLA), workflow (state machine),
                 routing, urgency, sla, notifications (in-app + email), timeline, realtime (WS hub),
                 suggestions (FAQ / similar cases / smart replies), reports (Excel / PDF), jobs (background)
  app/ml/        dataset (multilingual), classifier (TF-IDF + Logistic Regression), evaluate, training
                 (retraining + registry + hot swap), embeddings (provider interface + vector search), pii
  migrations/    Alembic
```

Design choices for local development, all swappable without code changes elsewhere:

- **SQLite by default**, PostgreSQL through `QOLDAU_DATABASE_URL` (Docker Compose uses Postgres).
- The **in-process WebSocket hub** and **APScheduler** stand in for Redis pub/sub and Celery. `services/realtime.py` is the single place to plug in Redis when running several instances.
- **Background jobs** (exports, retraining, re-indexing) run on a small thread pool after the transaction commits (`services/jobs.py`); swap in Celery there.
- **Report files** are stored privately in `backend/exports/` and downloaded through HMAC-signed links valid 24 h (stand-in for S3).
- **Embeddings** default to a built-in multilingual provider (no model download) and are searched in memory; set `QOLDAU_EMBEDDING_PROVIDER=sentence-transformers` for `intfloat/multilingual-e5-small`, and `ml/embeddings.search` is the place to switch to pgvector.
- **Email** is written to the `email_outbox` table and sent over SMTP only when `QOLDAU_SMTP_HOST` is set.
- **Attachments** are stored privately on disk and downloaded through HMAC-signed, expiring URLs. Scanning is a built-in hook (blocks executables and the EICAR test signature); swap in ClamAV for production.
- The UI uses hand-written components in the shadcn/ui style rather than the shadcn CLI.

## User story traceability

| Story | Where it lives |
|---|---|
| US1 Submission UI | `requests/new`: required category/subject/description, inline red errors, live character counter (Submit disabled over 2000), drag-and-drop on desktop / wide 44px “Choose file” button on mobile, live AI category preview, success animation + modal showing the request ID |
| US2 Visual status tracking | `components/ProgressTracker.tsx`: active stage highlighted, future stages dimmed, timestamps; horizontal ≥768px, vertical below; updates live over `WS /ws/requests/{id}` |
| US3 Kanban | `agent/board`: New / In Progress / Waiting for Student / Resolved columns; drag-and-drop calls `PATCH /requests/{id}/status` (reverts on 409); Critical cards get a pulsing red border + warning icon and sort to the top |
| US4 Mobile | Hamburger slide-out drawer with dimmed, inert background; 44×44 touch targets; no horizontal page scroll |
| US5 Classification | `ml/classifier.py`: 10 categories, confidence + top-3 alternatives + explaining keywords; < 0.60 confidence or vague text → **Needs Review**, Triage queue, no unit |
| US6 Urgency | `services/urgency.py`: category weight + editable keywords + date rules (today/tomorrow/dd.mm) + ML confidence → 0–100 score; health/safety keywords force Critical and alert the unit immediately |
| US7 Routing | `services/routing.py`: routing_rules → unit, least-loaded online agent (round-robin tie-break), unit-queue fallback, `routing_log` reason such as `rule: Finance & Scholarships -> Finance Office` |
| US8 Workflow & notifications | `services/workflow.py`: allowed transitions only (409 “Transition not allowed”), `status_history`, per-category templates (Document: Request → Prepare → Ready for Pickup), bell badge over WebSocket + email |
| US9 AI override | AI Decision panel (confidence bar, alternatives, highlighted keywords, urgency reasons); override requires a reason, re-routes, and stores `ai_feedback`; internal notes (yellow lock) are never sent to students |
| US11 Timeline & search | `GET /requests/{id}/timeline`, `RequestList` with ID/keyword search, status/category/priority/date filters, 20 per page |
| US12 SLA | `services/sla.py`: policy per priority (optional working-hours calendar); warning at 80%, at breach escalate to unit head and raise priority one level; paused while Waiting for Student; checked every minute; auto-close 7 days after Resolved |
| US13 Analytics | `GET /analytics/dashboard`: KPI cards plus charts and tables; unit heads and agents are locked to their own unit |
| US14 Admin | `/admin`: CRUD for categories, units, routing rules, SLA policies, urgency keywords, users & roles; audit log (old → new); 403 for non-admins; units with open requests can’t be deleted |
| US15 Messaging & CSAT | Real-time chat with typing indicator, read receipts, PDF/JPG/PNG/DOCX ≤ 10 MB, retry on failed send; 1–5 star rating after Resolved; ≤ 2 reopens the request and notifies the unit head |
| US10 / US16 Scrum | `docs/sprint-report.md`, `python -m app.ml.evaluate` |
| US17 Report export | `services/reports.py`, `api/export.py`: Export menu on Analytics and Unit requests → background job → Reports page + bell → signed 24 h link. Excel has 6 sheets, PDF has KPIs and charts, numbers come from the dashboard's own functions. Unit heads only get their own unit; students and agents get 403 |
| US18 AI retraining | `ml/training.py`: seed data + agent corrections, hold-out metrics + confusion matrix, versioned artifacts, auto-promotion only if macro-F1 ≥ active, Activate / Roll back with hot swap, weekly schedule. Page: `admin/models` |
| US19 Smart replies | `services/suggestions.py`: templates + similar resolved cases + KB in the request's language, PII masked, no internal notes; Insert never sends; used / edited / ignored logged |
| US20 FAQ suggestions | "Maybe this helps" on New request: published FAQ (inline, helpful votes) + anonymised solved cases; "This solved my problem" → deflection KPI |
| US21 Knowledge base | `api/kb.py`, page `kb`: KZ/RU/EN translations, draft → published → archived, version history with diff, agents propose and unit heads publish (403 otherwise), reply templates with placeholders |
| US22 Scrum | `docs/SPRINT4_PLAN.md`, `docs/SPRINT4_DEMO.md` |

## Known limitations

- The base training set is synthetic (898 template-generated samples in 3 languages), so its held-out accuracy (99%) is inflated. Retraining now adds agent corrections, and those versions score lower (about 91–96%), which is a more honest number.
- The priority model is trained and versioned, but urgency scoring still uses the Sprint 2 rules engine.
- Migration 0002 is written for SQLite and PostgreSQL but has only been run on SQLite.
- Not yet run against real PostgreSQL or Docker in this environment. Local runs and tests used SQLite.
- Drag-and-drop on the Kanban board is verified in the browser through pointer events. A touch sensor is configured for phones but has not been tested on physical iOS/Android devices.
