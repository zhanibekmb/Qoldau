demo:
	cd backend && python -m app.seed --reset --demo

test:
	cd backend && python -m pytest -q
	cd frontend && npx tsc --noEmit && npm run lint

.PHONY: demo test
