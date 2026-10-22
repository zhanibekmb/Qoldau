# Sprint 4 Review: 10-minute demo script

## Setup (once, about 20 s)

```bash
make demo            # or: cd backend && python -m app.seed --reset --demo
cd backend && uvicorn app.main:app --port 8000
cd frontend && npm run dev
```

This **erases the database** and loads: 520+ requests, 60 FAQ articles (20 topics × KZ/RU/EN), 15 reply templates,
classifier v1.1 (archived) and v1.2 (active), and 275+ agent labels collected since v1.2.

Accounts (password `Qoldau123!`): student `student@qoldau.edu.kz`, agent `agent1.it@qoldau.edu.kz`,
unit head `head.registrar@qoldau.edu.kz`, admin `admin@qoldau.edu.kz`.

## Script

| Min | Who | Click by click | Say / show |
|---|---|---|---|
| 0:00 | — | Analytics (admin) | Sprint goal: answers come faster, fewer requests are needed, the model keeps learning, management gets reports |
| 0:30 | Unit head (Registrar) | Knowledge base → New article → EN tab: "Ordering a transcript" + answer → Save draft → RU tab, then KZ tab, same → Publish on each | US21: one article, three languages; version 1; the dot on each tab shows its status |
| 2:00 | Agent (IT) | Open a resolved IT ticket → **Propose FAQ** | Draft created, unit head notified (bell). Back in KB the agent has no Publish button; the API returns 403 |
| 3:00 | Student (switch UI to RU) | New request → type «Как получить справку с места учебы» | US20: "Maybe this helps" shows «Справка с места учёбы» (Registrar Office) and solved cases with names hidden. **Read answer** → 👍 → **This solved my problem** → "Glad it helped!", no request created |
| 4:30 | Student | New request → «Не могу войти в Moodle, пишет неверный пароль» → Submit | Request goes to the IT Help Desk |
| 5:00 | Agent (IT) | Open that ticket → Smart replies | US19: 3 Russian suggestions with source and relevance; the Moodle template is #1. **Insert** → edit a word → Send. Logged as "edited" |
| 6:30 | Admin | AI models | Active v1.2, "275 / 200" new labels → **Retrain now** → Confirm. Live log: classifier v1.3 activated because macro-F1 ≥ v1.2; the priority model may stay a candidate. Open **Details** for per-category F1 and the confusion matrix |
| 8:00 | Admin | v1.2 → **Roll back** → Confirm | US18: switched without restart; "Serving v1.2" |
| 8:30 | Admin | Analytics → Last 30 days, IT Help Desk → Export → Excel; then Export → PDF | US17: toast, then a bell when ready → Reports → Download. Excel has 6 sheets; totals equal the dashboard |
| 9:30 | Admin | Analytics KPI row | Self-service rate (the student's deflection), Smart-reply usage, AI accuracy |

## KPIs to quote

- Model accuracy and macro-F1, v1.2 vs v1.3 (Model Management)
- Self-service deflection rate and smart-reply usage (Analytics)
- Speed: FAQ suggestions in tens of ms (target 800 ms), smart replies about 20 ms (target 1.5 s),
  10,000-row Excel export in about 3 s (target 30 s)

## If something goes wrong

- No suggestions: `cd backend && python -m app.ml.embeddings --reindex`
- Retrain says "Not enough new feedback": tick **Force**
- To restart the demo: `make demo` again (erases everything)
