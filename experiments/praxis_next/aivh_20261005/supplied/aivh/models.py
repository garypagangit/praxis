"""Classifiers for AIVH. Thin wrappers that all expose predict_proba
over a fixed class order, so the conformal gate can consume any of them."""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer


def make_model(kind: str = "gbm"):
    if kind == "gbm":
        return HistGradientBoostingClassifier(
            max_depth=4, learning_rate=0.08, max_iter=300,
            l2_regularization=1.0, early_stopping=True, random_state=0,
            class_weight="balanced",
        )
    if kind == "logreg":
        return Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0)),
        ])
    raise ValueError(kind)


class VerbNgramModel:
    """TF-IDF over command-verb n-grams → logistic regression.
    Checks whether the hand-engineered features add anything over a bag of
    commands. Consumes raw Sessions, not the feature matrix."""

    def __init__(self, ngram=(1, 2)):
        self.vec = TfidfVectorizer(ngram_range=ngram, min_df=2, token_pattern=r"[^\s]+")
        self.clf = LogisticRegression(max_iter=2000, class_weight="balanced")
        self.classes_ = None

    @staticmethod
    def _doc(session):
        from .features import _verb
        return " ".join(_verb(c.text) for c in session.commands if c.text)

    def fit(self, sessions, y):
        X = self.vec.fit_transform(self._doc(s) for s in sessions)
        self.clf.fit(X, y)
        self.classes_ = list(self.clf.classes_)
        return self

    def predict_proba(self, sessions):
        X = self.vec.transform(self._doc(s) for s in sessions)
        return self.clf.predict_proba(X)
