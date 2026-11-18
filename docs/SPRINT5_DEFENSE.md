# Sprint 5 defense notes

Use `presentations/Qoldau_Sprint5_Review.pdf` on the projector. Keep the PPTX as the editable copy. The slides follow the 13-slide Sprint 4 review style.

## The claim to make

> Sprint 5 implementation is complete in five separate pull requests. The RBAC audit, shared API rate limits, six browser journeys, PostgreSQL migration checks, admin localization and priority-model decision are verified. The pull requests remain open because we were asked not to merge into `main`. This is an implementation review, not a claim that a public production deployment has happened.

This distinction matters: the earlier Sprint 4 roadmap mentioned load tests, pgvector, ClamAV and a full OWASP review. Those are **not** delivered by the current PR set. A public launch also needs a host, domain, DNS, secrets and a restore exercise.

## Five-minute English script

1. **Slides 1–3 (35 s):** “Qoldau already accepts student requests in Kazakh, Russian and English, classifies and routes them, and tracks their status. Sprint 5 focused on access boundaries, abuse controls, connected browser tests and a production path.”
2. **Slide 4 (25 s):** “We tracked five issues on our private board and opened one PR for each. All checks are green. We intentionally left `main` untouched.”
3. **Slide 5 (40 s):** “A student sees their own requests. Staff see assigned or authorized unit requests. Triage staff can handle the shared review queue. The same visibility rule now applies to API, WebSocket and file downloads, including signed links.”
4. **Slide 6 (35 s):** “Configurable limits protect login, writes, AI suggestions, exports and retraining. Counters live in the database so multiple workers share them. Exceeding a limit returns HTTP 429 with Retry-After. Proxy headers are trusted only from configured peers.”
5. **Slide 7 (35 s):** “Six Playwright scenarios use a real Chromium browser: student submission, agent work, FAQ publication, admin keyword editing, language switching and report export. They pass locally and in GitHub Actions.”
6. **Slide 8 (35 s):** “Our PostgreSQL workflow runs Alembic migrations and the backend suite on a PostgreSQL service. We prepared a Compose stack with HTTPS, readiness checks and a first-admin bootstrap without demo users. It is a deployment plan, not a live rollout.”
7. **Slides 9–10 (45 s):** “The remaining admin labels now work in Russian and Kazakh. We kept the rule-based priority scorer live: the demo priority model has macro-F1 0.750 and High-class F1 0.400, with no real priority corrections. Critical keywords still force Critical.”
8. **Slides 11–13 (50 s):** “On the combined branch, 68 backend tests and six browser scenarios passed. Backend statement coverage was 81% in the local pytest-cov run. All five PRs have green CI. We are ready for a Sprint 5 implementation review; merging and public deployment are separate steps.”

## Short Russian version

«За Спринт 5 мы закрыли реализацию пяти задач в отдельных PR: проверили права доступа, добавили общие лимиты API, шесть браузерных сценариев, проверку миграций на PostgreSQL и перевод админки. На объединённой ветке прошли 68 backend тестов и шесть браузерных сценариев; покрытие backend по строкам кода — 81%. Все PR зелёные, но в `main` они ещё не слиты по нашему условию. На живом сервере система пока не развёрнута. Модель приоритета оставили в режиме оценки, поскольку на демонстрационных данных она недостаточно надёжна для срочных обращений».

## Likely questions

| Question | Answer |
|---|---|
| Is Sprint 5 in `main`? | No. PRs #6–#10 are open, mergeable and green. The instruction was to use separate branches and not merge into `main`. |
| Is Qoldau deployed for real users? | No. PR #8 contains a production configuration and runbook; a host, domain, secrets and deployment checks are still required. |
| What does 81% mean? | Statement coverage of `backend/app` from `pytest backend/tests --cov=backend/app`; it does not measure browser code, performance or security. |
| Why is the priority model not live? | The demo model's High-class F1 is 0.400, with zero real priority corrections in its training registry. The existing rules keep a Critical floor for safety keywords and at least High for urgent workflows. |
| How do limits work across workers? | Each request increments an atomic, hashed database bucket. The same counter is visible to all API workers. |
| What is still missing from the Sprint 4 roadmap? | Load testing, pgvector integration, ClamAV and a full OWASP review remain future hardening work. Do not present them as completed. |

## Evidence and demo path

- PRs: [#6 RBAC](https://github.com/zhanibekmb/Qoldau/pull/6), [#7 limits](https://github.com/zhanibekmb/Qoldau/pull/7), [#8 PostgreSQL](https://github.com/zhanibekmb/Qoldau/pull/8), [#9 browser tests](https://github.com/zhanibekmb/Qoldau/pull/9), [#10 localization](https://github.com/zhanibekmb/Qoldau/pull/10).
- Project: <https://github.com/users/berikside/projects/2/views/1>.
- On this Mac, the combined local worktree is `/Users/berikzumagaliev/Documents/ChatGPT/PM-sprint5-integration`. It contains all five PRs and was used for the 68-test and six-browser-scenario checks. The demo database is isolated from production.
- For the live demo, double-click `scripts/sprint5_demo.command` in that worktree. Wait for “Qoldau Sprint 5 demo is ready,” then use the demo accounts listed in `README.md`. Keep the Terminal window open during the talk and press Control-C afterward. The `sprint5/demo` preview branch has the same combined code and launcher.
- Before presenting, open the PDF full-screen and keep slides 7, 9 and 11 as a fallback if a live browser demo is unavailable. The slides contain the screenshot and verification evidence needed for a complete explanation.
