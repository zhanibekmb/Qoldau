# Model evaluation report

Generated 2026-10-21 13:24 UTC · model `tfidf-lr-202610211304` · tfidf(word1-2+char2-5)+logreg

| Metric | Value | Target |
|---|---|---|
| Accuracy (held-out split, n=180) | 99.4% | >= 85% |
| Macro F1 (held-out split) | 0.994 | >= 0.80 |
| Accuracy on hand-written unseen requests (n=15) | 100.0% | - |
| Routing correctness (n=15) | 100.0% | - |

Note: the held-out split comes from the same template generator as the training data, so it overstates real-world accuracy; the hand-written set is the more honest signal. Agent overrides (ai_feedback) are the source for retraining in Sprint 4.

## Per-class (held-out split)

| Category | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Academic | 1.00 | 1.00 | 1.00 | 24 |
| Documents & Certificates | 1.00 | 1.00 | 1.00 | 18 |
| Dormitory & Housing | 1.00 | 1.00 | 1.00 | 18 |
| Finance & Scholarships | 1.00 | 1.00 | 1.00 | 19 |
| Health & Wellbeing | 1.00 | 1.00 | 1.00 | 17 |
| IT Support | 0.95 | 1.00 | 0.98 | 20 |
| International Office | 1.00 | 1.00 | 1.00 | 16 |
| Library | 1.00 | 0.93 | 0.97 | 15 |
| Other | 1.00 | 1.00 | 1.00 | 14 |
| Registration & Enrollment | 1.00 | 1.00 | 1.00 | 19 |
