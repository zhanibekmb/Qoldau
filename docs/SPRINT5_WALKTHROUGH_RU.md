# Как показать Спринт 5 преподавателю и Жанибеку

**Начни с [одного общего PR #12](https://github.com/zhanibekmb/Qoldau/pull/12) или [ветки sprint5/demo](https://github.com/zhanibekmb/Qoldau/tree/sprint5/demo).** Там собраны пять отдельных PR с кодом, презентация и локальный запуск. PR #12 оставлен черновиком только для демонстрации; сливать его вместо отдельных PR не нужно. На главной странице GitHub по умолчанию выбрана ветка `main`; там остаётся Спринт 4, поскольку мы договорились не сливать PR самостоятельно.

## Подготовка перед выступлением

1. Скачай или открой [PDF презентации](https://github.com/zhanibekmb/Qoldau/blob/sprint5/demo/presentations/Qoldau_Sprint5_Review.pdf) на весь экран. [PPTX](https://github.com/zhanibekmb/Qoldau/blob/sprint5/demo/presentations/Qoldau_Sprint5_Review.pptx) — редактируемая версия с заметками к слайдам.
2. Держи рядом [готовый текст на пять минут и ответы на вопросы](SPRINT5_DEFENSE.md). Слайды 7, 9 и 11 содержат доказательства, если живое демо не запустится.
3. Для живого показа на этом Mac открой `scripts/sprint5_demo.command` в локальной папке `PM-sprint5-integration`. Дождись сообщения `Qoldau Sprint 5 demo is ready`. Откроется `http://127.0.0.1:3000/login`. Оставь окно Terminal открытым; после защиты нажми Control-C. Данные примера хранятся отдельно в `~/.cache/qoldau-sprint5-demo`.

## Маршрут показа: 7–8 минут

| Время | Что открыть | Что сказать |
|---|---|---|
| 0:00–0:40 | Слайды 1–4 и [доска Спринта 5](https://github.com/users/berikside/projects/2/views/1) | «У нас пять задач. Реализация каждой вынесена в отдельный PR; в `main` пока ничего не слито». На доске задачи остаются `In Progress` именно из-за открытых PR. |
| 0:40–2:00 | Слайды 5–6 и PR [#6](https://github.com/zhanibekmb/Qoldau/pull/6), [#7](https://github.com/zhanibekmb/Qoldau/pull/7) | «Проверили доступ студента, агента и администратора к API, WebSocket и файлам. Добавили общие для API-воркеров лимиты с ответом 429». В PR нажми `Files changed` или `Checks`. |
| 2:00–3:00 | Слайд 7 и PR [#9](https://github.com/zhanibekmb/Qoldau/pull/9) | «Шесть сценариев Playwright проходят в браузере и в GitHub Actions: студент, агент, база знаний, настройки, языки, экспорт». Открой зелёные `Checks`. |
| 3:00–4:00 | Слайд 8 и PR [#8](https://github.com/zhanibekmb/Qoldau/pull/8) | «Миграции и backend проверяются на PostgreSQL в CI; подготовлены Compose, HTTPS и инструкции развёртывания. Это ещё не публичный сервер». |
| 4:00–5:00 | Слайды 9–10 и PR [#10](https://github.com/zhanibekmb/Qoldau/pull/10) | «Админка переключается на русский и казахский. Модель приоритета проверили, но не включили: на демоданных F1 для High равен 0,400». |
| 5:00–6:30 | Локальная демо-страница `http://127.0.0.1:3000/login` | Войти администратором, переключить RU → KZ, открыть настройки ключевых слов; затем показать обращение студента или экспорт отчёта. Подробный порядок — в [демо-инструкции](SPRINT5_DEMO.md). |
| 6:30–8:00 | Слайды 11–13 и [общая ветка](https://github.com/zhanibekmb/Qoldau/tree/sprint5/demo) | «На объединённой версии прошли 68 backend-тестов и 6 браузерных сценариев; локальное покрытие backend — 81%. Все отдельные PR прошли CI. Готовы к защите реализации; слияние и публичный запуск — следующие решения». |

Если времени только пять минут, используй [короткий сценарий](SPRINT5_DEFENSE.md) и пропусти живой браузер. PDF самодостаточен.

## Где именно находится новый код

| Задача | PR | Главные файлы для показа |
|---|---|---|
| Права доступа и видимость обращений | [#6](https://github.com/zhanibekmb/Qoldau/pull/6) | `backend/app/api/common.py`, `backend/tests/test_sprint5_rbac.py`, [матрица доступа](SPRINT5_RBAC.md) |
| Лимиты API | [#7](https://github.com/zhanibekmb/Qoldau/pull/7) | `backend/app/rate_limit.py`, `backend/tests/test_sprint5_rate_limits.py`, [описание](SPRINT5_RATE_LIMITS.md) |
| PostgreSQL и подготовка выпуска | [#8](https://github.com/zhanibekmb/Qoldau/pull/8) | `.github/workflows/postgres.yml`, `compose.production.yml`, [инструкция](SPRINT5_DEPLOY.md) |
| Проверки в браузере | [#9](https://github.com/zhanibekmb/Qoldau/pull/9) | `frontend/e2e/core-flows.spec.ts`, `.github/workflows/e2e.yml`, [описание](SPRINT5_E2E.md) |
| Перевод админки и решение по модели | [#10](https://github.com/zhanibekmb/Qoldau/pull/10) | `frontend/app/(app)/admin/page.tsx`, [решение по приоритету](SPRINT5_PRIORITY_DECISION.md) |
| Презентация | [#11](https://github.com/zhanibekmb/Qoldau/pull/11) | `presentations/Qoldau_Sprint5_Review.pdf`, `.pptx`, [заметки](SPRINT5_DEFENSE.md) |

PR #8 построен поверх #7, а #10 — поверх #9. Это видно по полю `base` в GitHub. Все отдельные PR открыты и прошли проверки; общий `sprint5/demo` нужен для показа результата вместе.

## Что отвечать на главный вопрос

> **Готов ли Спринт 5?** Реализация пяти запланированных задач готова и проверена в ветках. Слияние в `main` специально не выполнялось. Публичное развёртывание, нагрузочные тесты, полная проверка OWASP, ClamAV и pgvector пока не завершены, поэтому не называем это production-релизом.

История Git записана от настроенного на этом Mac аккаунта `berikside`. Код и материалы Спринта 5 были подготовлены с помощью Codex; базовый проект и Спринты 1–4 уже существовали. При защите можно честно сказать, что использовался AI-помощник, а содержание проверяется через PR, тесты и демонстрацию.
