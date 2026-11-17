# Sprint 5 priority model decision

**Decision (2026-11-17):** Keep the rules-based urgency scorer as the live source of request priority. Do not feed the trained priority classifier into live scoring or automatically promote its output.

## Evidence

- The active demo priority model (`v1.2`) reports accuracy **0.8571** and macro-F1 **0.7502** on a 98-item hold-out split. Its **High** F1 is **0.4**; six of nine High examples were predicted as another class (five as Medium, one as Critical). One of eight Critical examples was predicted Medium.
- The priority model's training set comes from past request priorities plus agent corrections (`priority_dataset` in `backend/app/ml/training.py`). The supplied demo registry shows **390** training examples and **zero** priority corrections for this model. The demo requests and labels are generated, so these metrics do not measure performance on real student traffic.
- The live `services/urgency.score` combines category weights, editable EN/RU/KZ keywords, deadline signals, and explicit floors: a critical keyword forces Critical and an urgent workflow cannot score below High. The classifier confidence contributes at most five points. The trained priority model is registered and switchable for evaluation, but is not read by this live scorer.

## Reconsideration gate

Collect real, consented agent-reviewed priority labels across EN/RU/KZ, including Critical and High cases. Evaluate a held-out set and shadow predictions against the current scorer, reporting per-class recall, Critical/High under-triage, calibration, and language slices. Only propose live integration after the model improves those measures without weakening the existing critical-keyword and urgent-workflow floors. Keep an operator rollback path and a regression suite for safety cases.

This decision changes no live priority behavior. Existing urgency tests in `backend/tests/test_ai.py` cover the rules and critical floor; the Sprint 5 browser suite covers the admin configuration UI.
