"""TF-IDF + Logistic Regression baseline classifier (US5).

Word n-grams catch whole keywords ("transcript", "стипендия"), char n-grams make the model
robust to KZ/RU morphology and typos. The interface (predict -> Prediction) is model-agnostic
so a fine-tuned multilingual transformer can replace it later [Sprint 4-5].
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline

from ..config import get_settings
from . import dataset

ALGORITHM = "tfidf(word1-2+char2-5)+logreg"
MIN_CONTENT_WORDS = 2  # fewer distinct non-function words is too vague to route automatically

# Unseen, hand-written phrasings used as a sanity check alongside the held-out split.
HANDWRITTEN_EVAL = [
    ("I need a transcript of records for my visa application", "Documents & Certificates"),
    ("I cannot log in to Moodle, password reset does not work", "IT Support"),
    ("Scholarship application deadline is tomorrow and the upload button fails", "Finance & Scholarships"),
    ("I feel unsafe in my dorm room", "Health & Wellbeing"),
    ("My exam registration closes today and the system shows an error", "Registration & Enrollment"),
    ("The radiator in room 412 of dorm 3 is leaking", "Dormitory & Housing"),
    ("Can you give me a paper confirming that I study here, the embassy asks for it", "Documents & Certificates"),
    ("My teacher gave me 40 points but my answers were correct, I want a review of the grade", "Academic"),
    ("Stipend not received for October", "Finance & Scholarships"),
    ("Не работает почта outlook, пишет неверный пароль", "IT Support"),
    ("Хочу подать на обмен в Корею на весенний семестр", "International Office"),
    ("Кітапханадағы кітапты қайтару мерзімі өтіп кетті", "Library"),
    ("Мне очень тревожно и я не могу спать, нужен психолог", "Health & Wellbeing"),
    ("I want to add a second elective but registration is closed", "Registration & Enrollment"),
    ("book return question", "Library"),
]

_WORD = re.compile(r"\w+", re.UNICODE)
# Function words are never shown as "keywords that drove the decision".
STOPWORDS = set(
    "the a an of in on at to for my me i is am are was it this that and or but not no do does can with from "
    "have has be please help hello hi how what when where which who why you your our we yet still "
    "и в во на с со по к ко у о об от до за из не нет мне меня мой моя мою я это как что где когда "
    "мен менің бұл және мен де да ма ме ба бе па пе үшін керек".split()
)


@dataclass
class Prediction:
    category: str
    confidence: float
    alternatives: list[dict] = field(default_factory=list)  # top-3 [{category, confidence}]
    keywords: list[str] = field(default_factory=list)  # words that drove the decision
    model_version: str = ""
    needs_review: bool = False


def _build_pipeline() -> Pipeline:
    features = FeatureUnion([
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True, min_df=1,
                                 token_pattern=r"(?u)\b\w\w+\b")),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2,
                                 max_features=60000)),
    ])
    clf = LogisticRegression(C=40.0, max_iter=3000, class_weight="balanced")
    return Pipeline([("features", features), ("clf", clf)])


def train_and_evaluate(extra: list[tuple[str, str]] | None = None, seed: int = 42) -> tuple[Pipeline, dict]:
    data = dataset.generate(seed=seed) + (extra or [])
    texts = [t for t, _ in data]
    labels = [c for _, c in data]
    x_tr, x_te, y_tr, y_te = train_test_split(texts, labels, test_size=0.2, stratify=labels, random_state=seed)

    model = _build_pipeline().fit(x_tr, y_tr)
    pred = model.predict(x_te)
    hw_x = [t for t, _ in HANDWRITTEN_EVAL]
    hw_y = [c for _, c in HANDWRITTEN_EVAL]
    hw_pred = model.predict(hw_x)
    metrics = {
        "train_size": len(x_tr),
        "test_size": len(x_te),
        "accuracy": round(float(accuracy_score(y_te, pred)), 4),
        "macro_f1": round(float(f1_score(y_te, pred, average="macro")), 4),
        "handwritten_accuracy": round(float(accuracy_score(hw_y, hw_pred)), 4),
        "per_class": classification_report(y_te, pred, output_dict=True, zero_division=0),
    }
    # Final model is refit on all data.
    final = _build_pipeline().fit(texts, labels)
    return final, metrics


class Classifier:
    def __init__(self, pipeline: Pipeline, version: str):
        self.pipeline = pipeline
        self.version = version
        self.classes: list[str] = list(pipeline.classes_)
        word_vec: TfidfVectorizer = pipeline.named_steps["features"].transformer_list[0][1]
        self._word_vocab = word_vec.vocabulary_
        self._n_word = len(word_vec.vocabulary_)

    def predict(self, subject: str, description: str, threshold: float | None = None) -> Prediction:
        threshold = get_settings().confidence_threshold if threshold is None else threshold
        text = f"{subject or ''}. {description or ''}".strip(" .")
        words = _WORD.findall(text)
        if not words:
            return Prediction("Other", 0.0, [], [], self.version, needs_review=True)

        x = self.pipeline.named_steps["features"].transform([text])
        probs = self.pipeline.named_steps["clf"].predict_proba(x)[0]
        order = np.argsort(probs)[::-1]
        best = self.classes[order[0]]
        conf = float(probs[order[0]])
        # Vague / very short requests ("help please") are never trusted, whatever the model says.
        content = {w.lower() for w in words if w.lower() not in STOPWORDS and not w.isdigit()}
        if len(content) < MIN_CONTENT_WORDS:
            conf = min(conf, 0.35)
        alternatives = [{"category": self.classes[i], "confidence": round(float(probs[i]), 4)} for i in order[:3]]
        keywords = self._explain(x, order[0])
        return Prediction(best, round(conf, 4), alternatives, keywords, self.version, needs_review=conf < threshold)

    def _explain(self, x, class_idx: int, top: int = 5) -> list[str]:
        coef = self.pipeline.named_steps["clf"].coef_[class_idx]
        row = x.tocsr()
        idx = row.indices[row.indices < self._n_word]
        if len(idx) == 0:
            return []
        contrib = np.array([row[0, i] * coef[i] for i in idx])
        inv = {v: k for k, v in self._word_vocab.items() if v in set(idx.tolist())}
        ranked = [inv[idx[j]] for j in np.argsort(contrib)[::-1] if contrib[j] > 0]
        out: list[str] = []
        for term in ranked:
            if all(w in STOPWORDS for w in term.split()):
                continue
            if not any(term in o or o in term for o in out):
                out.append(term)
            if len(out) >= top:
                break
        return out


_lock = threading.Lock()
_instance: Classifier | None = None
_last_metrics: dict | None = None


def model_path():
    return get_settings().model_dir / "classifier.joblib"


def load_or_train() -> tuple[Classifier, dict | None]:
    """Load the persisted model, training (and saving) a new one if none exists."""
    global _instance, _last_metrics
    with _lock:
        if _instance is not None:
            return _instance, _last_metrics
        path = model_path()
        if path.exists():
            blob = joblib.load(path)
            _instance = Classifier(blob["pipeline"], blob["version"])
            _last_metrics = blob.get("metrics")
        else:
            pipeline, metrics = train_and_evaluate()
            version = "tfidf-lr-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
            path.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump({"pipeline": pipeline, "version": version, "metrics": metrics}, path)
            _instance = Classifier(pipeline, version)
            _last_metrics = metrics
        return _instance, _last_metrics


def get_classifier() -> Classifier:
    return load_or_train()[0]


# Hot swap (US18): the training module activates or rolls back versions without a restart.
def load_artifact(path) -> tuple[Classifier, dict | None]:
    blob = joblib.load(path)
    return Classifier(blob["pipeline"], blob["version"]), blob.get("metrics")


def swap(clf: Classifier, metrics: dict | None = None) -> None:
    global _instance, _last_metrics
    with _lock:
        _instance, _last_metrics = clf, metrics


def reset() -> None:
    """Forget the in-memory model; the next call loads the default artifact again."""
    global _instance, _last_metrics
    with _lock:
        _instance, _last_metrics = None, None


def current_version() -> str | None:
    return _instance.version if _instance is not None else None
