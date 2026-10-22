# Sprint 4 plan: intelligent features (US17–US22)

Deadline 06.11.2026. Source: `Sprint.xlsx` (S4 Backlog, story tabs, US17QATest–US22QATest, S4 Claude Code Prompts).
Sprint 5 items stay out of scope: full RBAC audit, rate limiting, full E2E suite, production deployment.

## 1. Starting point (Sprints 1–3)

- **Backend:** FastAPI + SQLAlchemy 2 + Alembic, SQLite by default (PostgreSQL in Docker). Pipeline
  `submit → classify (TF-IDF + LogReg) → urgency → routing → SLA`, workflow state machine, in-process
  WebSocket hub, APScheduler for SLA ticks. Background work is in-process by design (README "design choices").
- **Frontend:** Next.js 16 (App Router), Tailwind 4, Recharts, hand-written shadcn-style components, i18n KZ/RU/EN.
- **Data already prepared for Sprint 4:** `ai_feedback` (agent overrides), `model_registry`, `model_version` on requests.

### Gaps and bugs found while reviewing Sprints 1–3

| Finding | Action |
|---|---|
| `seed --reset` dropped tables but kept `alembic_version`, so the upgrade was a no-op and the seed silently fell back to `create_all` | Fixed: reset also drops `alembic_version` |
| `model_registry.version` was unique on its own, so classifier and priority models could not share `v1.3` | Fixed in migration 0002: unique `(model_type, version)` |
| Demo agent replies were English even on Russian / Kazakh requests | Fixed: replies follow the request language, per category (also feeds similar-case search) |
| README referred to `Sprint1.xlsx` | Fixed |
| Configuration (admin) screen labels are English-only | Open; Sprint 5 polish |
| Never run against PostgreSQL | Still open: migration 0002 is written for both dialects but has only been exercised on SQLite |

## 2. Build order and dependencies

US21 first, because US19 and US20 read the knowledge base. US18 needs US9's `ai_feedback`.

1. Data model + migration 0002 (all stories)
2. US21 Knowledge base API → UI
3. Embeddings + similarity service (US19 / US20)
4. US20 student suggestions → US19 smart replies
5. US18 retraining pipeline → Model Management UI
6. US17 report export API → UI
7. Acceptance tests, review, docs, demo (US22)

## 3. Data model (migration `0002_sprint4`, reversible)

| Table | Purpose |
|---|---|
| `report_jobs` | export jobs: type, filters (JSON), status, file key, requester, unit scope, row count |
| `model_registry` (extended) | `model_type` (classifier / priority), status (active / candidate / archived), train size, feedback count, artifact path, training run, activated by / at; metrics JSON holds per-class F1 and the confusion matrix |
| `training_runs` | status, trigger (manual / schedule), force flag, logs, result |
| `faq_articles`, `faq_article_versions` | articles per language (translations share a `slug`), status draft / published / archived, views, helpful votes; a version row per content edit |
| `reply_templates` | text with `{student_name} {request_id} {unit} {agent_name}`, category, unit, language, usage count |
| `content_embeddings` | vectors for FAQ, templates and resolved requests (packed float32) |
| `suggestion_events` | shown / opened / used / edited / ignored / deflected, per session or request |
| `requests.suggestions_shown` | suggestions the student saw before submitting |

## 4. Endpoints (`/api/v1`)

| Story | Endpoints |
|---|---|
| US21 | `GET/POST /admin/faq`, `GET/PUT/DELETE /admin/faq/{id}`, `POST /admin/faq/{id}/publish`, `/archive`, `GET /admin/faq/{id}/versions`, `POST /faq/{id}/vote`, CRUD `/admin/reply-templates`, `POST /requests/{id}/propose-faq`, `/save-template` |
| US20 | `POST /ai/similar`, `POST /suggestions/events` |
| US19 | `GET /ai/suggestions/{request_id}` |
| US18 | `POST /ai/retrain`, `GET /ai/training-runs[/{id}]`, `GET /ai/models[/{id}]`, `GET /ai/models/overview`, `POST /ai/models/{id}/activate`, `/rollback` |
| US17 | `POST /export/excel`, `/export/pdf`, `GET /export/jobs[/{id}]`, `GET /export/files/{id}` (signed) |
| Analytics | `/analytics/*` gain `priority` and `status` filters plus `deflections`, `deflection_rate`, `smart_reply_usage` KPIs |

## 5. Screens

- **Knowledge base** (`/kb`, staff): FAQ and Reply templates tabs, filters, editor with KZ / RU / EN tabs,
  rich text with preview, Save draft / Publish / Archive by role, version history with word diff, stats.
- **Ticket detail** (staff): Smart replies panel (Insert / Copy / Dismiss); Propose FAQ / Save reply as template on resolved tickets.
- **New request** (student): "Maybe this helps" panel with inline FAQ answers, helpful votes and "This solved my problem".
- **Analytics:** Self-service and Smart-reply KPI tiles; Export menu (also on Unit requests).
- **Reports** (`/reports`, unit head / admin): export jobs, status, download.
- **AI models** (`/admin/models`, admin): active models, feedback counter, Retrain (with force), live logs,
  versions table, Activate / Roll back, per-category F1, confusion matrix, accuracy across versions.

## 6. Decisions and deviations from the prompts

The prompts assume Celery, Redis, S3 and pgvector. This repo deliberately runs without them (see README), so each
is behind one swappable module instead:

| Prompt asks for | Built | Swap point |
|---|---|---|
| Celery workers + beat | in-process thread pool started after commit (`services/jobs.py`) + APScheduler (weekly retrain, model sync) | `jobs.submit` |
| Redis cache / pub-sub | in-process LRU caches; workers sync the active model from `model_registry` every 30 s | `ml/embeddings.encode_query`, `ml/training.sync_active_model` |
| S3 + signed URLs | private `exports/` directory + HMAC links valid 24 h | `services/reports.file_path` |
| pgvector HNSW | vectors in `content_embeddings`, cosine search in numpy (fast for tens of thousands of rows) | `ml/embeddings.search` |
| `intfloat/multilingual-e5-small` | default **local** provider (hashed char n-grams + classifier topic probabilities, no download); e5 available with `QOLDAU_EMBEDDING_PROVIDER=sentence-transformers` | `ml/embeddings.get_provider` |
| `backend/app/ai/...` | `backend/app/ml/...`, where the Sprint 2 model already lives | — |
| Priority model | trained, evaluated, versioned and switchable; urgency scoring still uses the Sprint 2 rules engine, so wiring the model in is a Sprint 5 decision | `services/urgency.score` |
| Playwright E2E for main flows | not added (the full E2E suite is Sprint 5); the flows were checked by hand in a browser, and the API tests below cover every scenario | — |

## 7. Risks

| Risk | Mitigation |
|---|---|
| Suggestions leak another student's data | PII masker (names, e-mails, phones, IDs, request IDs) on every reused case; only the final *public* staff reply is read; case IDs are opaque tokens; tests check all of this |
| A worse model gets activated | Auto-promotion only when macro-F1 ≥ active; candidates need an explicit admin action; one-click rollback |
| Hold-out metrics overstate quality (synthetic training data) | Feedback-based retraining adds real agent labels; the hand-written evaluation set is kept |
| Draft content reaches students | Search re-checks `status = published` after the vector lookup |
| Rich-text XSS | bleach allow-list on save; DOM-based allow-list again on render |

## 8. Acceptance scenarios → automated tests

All in `backend/tests/test_sprint4.py`; the full suite (Sprints 1–4) is 58 tests, all passing.

| Scenario (USxQATest) | Test | Result |
|---|---|---|
| US17 · Export analytics to Excel (6 sheets, totals = dashboard, audited) | `test_us17_admin_exports_analytics_to_excel` | pass |
| US17 · PDF report and access control (unit head sees own unit, student 403) | `test_us17_unit_head_pdf_is_scoped_and_students_get_403` | pass |
| US18 · Retrain from agent feedback (v1.3 registered and activated, logged) | `test_us18_retrain_from_feedback_auto_promotes` | pass |
| US18 · Rollback to previous model (no downtime, new requests use v1.2) | `test_us18_rollback_without_downtime` | pass |
| US18 · Lower-F1 model is not auto-activated (story fail script) | `test_us18_lower_f1_model_is_not_activated` | pass |
| US19 · Agent uses a smart reply (3 RU suggestions < 1.5 s, Insert fills placeholders, never sends) | `test_us19_agent_uses_a_smart_reply` | pass |
| US19 · Privacy of suggestions (PII masked, internal notes excluded, actions logged) | `test_us19_suggestions_mask_pii_and_exclude_internal_notes` | pass |
| US20 · FAQ suggestions while typing (< 800 ms, Enrollment certificate in top 3) | `test_us20_faq_suggestions_while_typing` | pass |
| US20 · Self-service deflection (no request, event recorded, KPI rises) | `test_us20_self_service_deflection` | pass |
| US20 · Never Draft or other students' data (story fail script) | `test_us20_never_draft_or_other_students_data` | pass |
| US21 · Publish an FAQ article (KZ/RU/EN, version 1, in suggestions) | `test_us21_unit_head_publishes_faq_in_three_languages` | pass |
| US21 · Agent proposes an FAQ (Draft, head notified, publish 403) | `test_us21_agent_proposes_faq_and_cannot_publish` | pass |
| US22 · Standup / Sprint Review | process scenarios, covered by `docs/SPRINT4_DEMO.md` and the Sprint Review | — |

Extra checks: cross-language FAQ search (KZ/RU/EN → same article, < 300 ms), the PII masker, language detection,
rich-text sanitising, versioning on edit, and Save reply as template.

Measured outside the test suite: 10,000-row Excel export in 2.5 s and PDF in 0.4 s (target < 30 s);
FAQ suggestions in 5–35 ms; smart replies in about 20 ms.
