# Sprint 1–3 delivery report

| Sprint | Stories | Points | Status |
|---|---|---|---|
| 1 — Core portal UI (deadline 25.09.2026) | US1 (4), US2 (5), US3 (6), US4 (4) | 19 | Done |
| 2 — AI core (30.09.2026) | US5 (8), US6 (6), US7 (6), US8 (7), US9 (5), US10 (3) | 35 | Done |
| 3 — Tracking, SLA, analytics, admin, messaging (16.10.2026) | US11 (5), US12 (6), US13 (8), US14 (6), US15 (5), US16 (3) | 33 | Done |

## Definition of Done check

- Given/When/Then scenarios from US1QATest–US15QATest: the backend scenarios are covered by `backend/tests` (40 tests, all green). UI scenarios (success animation, red counter, progress bar, Kanban drag, hamburger drawer, live chat) were checked by hand in Chrome.
- API documented in OpenAPI at `/api/docs`.
- Responsive UI checked at 375px (no horizontal scroll, drawer navigation, touch-sized file button).
- Model quality: see `model-evaluation.md` (targets: accuracy ≥ 85%, macro F1 ≥ 0.80).

## Dependencies found during delivery

- US5 → US6/US7: urgency and routing consume classifier output. Resolved by running them in one pipeline (`services/pipeline.py`).
- US12 ↔ US14: SLA policies and urgency keywords are admin-editable tables, read on every request. No redeploy is needed.

## Sprint 4–5 backlog (refined, not yet built)

| Story | Notes | Estimate |
|---|---|---|
| Report export (Excel/PDF) | `POST /export/excel`, `/export/pdf` reusing `analytics.compute` | 5 |
| AI retraining from agent feedback | `POST /ai/retrain`: merge `ai_feedback` into the dataset, register a new `model_registry` version, activate it if F1 improves | 8 |
| Multilingual transformer | Fine-tune xlm-roberta / multilingual-e5 behind the same `Classifier.predict` interface | 8 |
| Smart replies & similar requests | Embeddings over resolved requests; `GET /ai/suggestions/{id}` | 6 |
| Security hardening | Rate limiting, full RBAC audit, OWASP Top-10 review, ClamAV scanning | 6 |
| E2E & release | Playwright suite, coverage ≥ 70%, Postgres/Redis deployment | 8 |
