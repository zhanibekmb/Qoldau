# Sprint 4 changelog

## Added

- **US21 Knowledge base:** FAQ articles in KZ/RU/EN (translations grouped by slug), draft → published → archived,
  a version row on every edit, helpful votes and views, reply templates with placeholders. Agents create drafts
  ("Propose FAQ" from a resolved ticket notifies the unit head); only an admin or the unit head of the article's
  unit can publish (HTTP 403 otherwise). Rich text is sanitised with bleach. Publishing re-indexes the article right after commit.
- **US20 Suggestions for students:** "Maybe this helps" on the New Request form after 15 characters (500 ms
  debounce): up to 3 published FAQ answers (read inline, vote helpful) and up to 3 anonymised solved requests.
  "This solved my problem" ends the flow without a request and counts as a deflection; otherwise the suggestions
  shown are saved with the request.
- **US19 Smart replies:** top-3 suggestions on the ticket from templates, similar resolved cases and KB articles,
  in the request's language, with source and relevance. Insert fills placeholders and puts the text in the reply
  box; it is never sent automatically. Used / edited / ignored are logged. Optional LLM rewriter interface behind
  `QOLDAU_SMART_REPLY_LLM_ENABLED` (no provider ships).
- **US18 Retraining & model management:** dataset builder (seed data + agent corrections, latest wins), stratified
  hold-out evaluation (accuracy, macro-F1, per-class F1, confusion matrix), versioned artifacts, registry, automatic
  promotion only when macro-F1 ≥ active, Activate / Roll back with hot swap (this worker at once, other workers within
  30 s), weekly scheduled retrain, 200-correction threshold with Force. Admin-only Model Management page.
- **US17 Report export:** Excel (Summary, By Category, By Unit, SLA, AI Accuracy, Raw Requests) and branded PDF
  (KPIs, charts, SLA, AI accuracy) from the same functions as the dashboard. Background jobs, Reports page,
  bell notification, signed 24 h links. Unit heads are scoped to their unit in the query; students and agents
  get 403. Student e-mails are masked unless the requester is an admin. Every export is in the audit log.
- **Analytics:** Self-service deflection rate and Smart-reply usage KPIs; `priority` / `status` filters.
- **Embeddings service** (`app/ml/embeddings.py`): provider interface (local default, sentence-transformers optional),
  vector index table, query cache, `python -m app.ml.embeddings --reindex`; resolved requests are indexed automatically.
- **PII masker** (`app/ml/pii.py`): names, e-mails, phones, long ID numbers, request IDs, self-introductions (EN/RU/KZ).
- **Seed:** 20 FAQ topics × 3 languages, 15 reply templates, language-aware agent replies; `--demo` adds model
  versions v1.1 / v1.2 and 260 agent-reviewed labels. `make demo`.
- 18 new backend tests (58 in total).

## Changed

- `model_registry` is unique per `(model_type, version)` and tracks status, artifact and activation.
- `Modal` takes `size`; navigation highlights the most specific match.
- Docker image installs DejaVu fonts (Cyrillic in PDFs); compose adds `exports` and `models` volumes.

## Fixed

- `seed --reset` now also drops `alembic_version`, so migrations run again instead of the `create_all` fallback.

## Review notes (security / quality)

- Every new endpoint has a role check: KB and smart replies are staff-only, exports are head/admin, model management is admin-only.
  Students reach only `/ai/similar`, `/suggestions/events` and `/faq/{id}/vote`.
- Internal notes never reach suggestions or exports. Similar cases use opaque IDs and masked text, and exclude the student's own requests.
- Drafts and archived articles are filtered again after vector search.
- Lists use `joinedload`; suggestion lookups batch-load their rows (no N+1 per hit).
- Background jobs mark themselves `failed` with the error and notify the requester; a second training run is rejected (409) while one is running.

## New configuration

`QOLDAU_EXPORT_DIR`, `QOLDAU_EXPORT_LINK_HOURS`, `QOLDAU_EMBEDDING_PROVIDER`, `QOLDAU_EMBEDDING_MODEL`,
`QOLDAU_RETRAIN_MIN_FEEDBACK`, `QOLDAU_RETRAIN_WEEKLY`, `QOLDAU_MODEL_SYNC_SECONDS`,
`QOLDAU_SMART_REPLY_LLM_ENABLED`, `QOLDAU_SMART_REPLY_LLM_PROVIDER`, `QOLDAU_JOBS_INLINE` (tests). See `backend/.env.example`.
