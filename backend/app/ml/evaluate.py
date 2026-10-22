"""Model evaluation report for Sprint Review (US10): accuracy, macro F1, routing correctness.

Usage:  python -m app.ml.evaluate            (prints report, writes docs/model-evaluation.md)
        python -m app.ml.evaluate --retrain  (retrains and replaces the persisted model first)
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path

from ..db import SessionLocal
from ..models import Category, RoutingRule
from . import classifier

REPORT = Path(__file__).resolve().parents[3] / "docs" / "model-evaluation.md"


def routing_correctness(clf: classifier.Classifier) -> tuple[float | None, int]:
    """Share of hand-written requests whose predicted category routes to the same unit as the true one."""
    db = SessionLocal()
    try:
        unit_of: dict[str, int | None] = {}
        for c in db.query(Category):
            rule = db.query(RoutingRule).filter_by(category_id=c.id, is_active=True).order_by(RoutingRule.id.desc()).first()
            unit_of[c.name] = rule.unit_id if rule else c.unit_id
    finally:
        db.close()
    if not unit_of:
        return None, 0
    ok = sum(unit_of.get(clf.predict("", text).category) == unit_of.get(label) for text, label in classifier.HANDWRITTEN_EVAL)
    return ok / len(classifier.HANDWRITTEN_EVAL), len(classifier.HANDWRITTEN_EVAL)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--retrain", action="store_true")
    args = ap.parse_args()
    if args.retrain:
        classifier.model_path().unlink(missing_ok=True)
        classifier._instance = None
    clf, metrics = classifier.load_or_train()
    if metrics is None:
        _, metrics = classifier.train_and_evaluate()
    routing, n = routing_correctness(clf)

    lines = [
        "# Model evaluation report",
        "",
        f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · model `{clf.version}` · {classifier.ALGORITHM}",
        "",
        "| Metric | Value | Target |",
        "|---|---|---|",
        f"| Accuracy (held-out split, n={metrics['test_size']}) | {metrics['accuracy']:.1%} | >= 85% |",
        f"| Macro F1 (held-out split) | {metrics['macro_f1']:.3f} | >= 0.80 |",
        f"| Accuracy on hand-written unseen requests (n={len(classifier.HANDWRITTEN_EVAL)}) | {metrics['handwritten_accuracy']:.1%} | - |",
        f"| Routing correctness (n={n}) | {routing:.1%} |" + " - |" if routing is not None else "| Routing correctness | (no DB) | - |",
        "",
        "Note: the held-out split comes from the same template generator as the training data, so it "
        "overstates real-world accuracy; the hand-written set is the more honest signal. Agent overrides "
        "(ai_feedback) are the source for retraining in Sprint 4.",
        "",
        "## Per-class (held-out split)",
        "",
        "| Category | Precision | Recall | F1 | Support |",
        "|---|---|---|---|---|",
    ]
    for name, m in metrics["per_class"].items():
        if isinstance(m, dict) and "support" in m and name not in ("macro avg", "weighted avg"):
            lines.append(f"| {name} | {m['precision']:.2f} | {m['recall']:.2f} | {m['f1-score']:.2f} | {int(m['support'])} |")
    report = "\n".join(lines) + "\n"
    print(report)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print(f"Written to {REPORT}")


if __name__ == "__main__":
    main()
