from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class BiLSTMModel:
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.model = None
        self.classes_: np.ndarray | None = None
        self.seq_len = int(self.params.get("seq_len", 4))
        self.seed = int(self.params.get("seed", self.params.get("random_state", 42)))

    def fit(self, x: np.ndarray, y: np.ndarray) -> "BiLSTMModel":
        try:
            import torch
            from torch import nn
            from torch.utils.data import DataLoader, TensorDataset
        except Exception:
            self.classes_, counts = np.unique(y, return_counts=True)
            self.priors_ = counts / counts.sum()
            return self

        torch.manual_seed(self.seed)
        self.classes_ = np.unique(y)
        class_to_dense = {value: idx for idx, value in enumerate(self.classes_)}
        dense_y = np.asarray([class_to_dense[value] for value in y], dtype=np.int64)
        x_seq = _tabular_to_sequence(x.astype(np.float32), self.seq_len)
        hidden_dim = int(self.params.get("hidden_dim", 32))
        batch_size = int(self.params.get("batch_size", 128))
        epochs = int(self.params.get("epochs", 8))
        lr = float(self.params.get("lr", 1e-3))
        self.model = _build_tiny_bilstm(x_seq.shape[2], hidden_dim, len(self.classes_))
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        loss_fn = nn.CrossEntropyLoss()
        dataset = TensorDataset(torch.from_numpy(x_seq), torch.from_numpy(dense_y))
        generator = torch.Generator().manual_seed(self.seed)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, generator=generator)
        self.model.train()
        for _ in range(epochs):
            for xb, yb in loader:
                optimizer.zero_grad()
                loss = loss_fn(self.model(xb), yb)
                loss.backward()
                optimizer.step()
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        if self.classes_ is None:
            raise RuntimeError("BiLSTMModel must be fit before predict_proba.")
        if self.model is not None:
            import torch

            self.model.eval()
            x_seq = _tabular_to_sequence(x.astype(np.float32), self.seq_len)
            with torch.no_grad():
                logits = self.model(torch.from_numpy(x_seq))
                probs = torch.softmax(logits, dim=1).cpu().numpy()
            return probs
        return np.tile(self.priors_, (len(x), 1))

    def predict(self, x: np.ndarray) -> np.ndarray:
        if self.classes_ is None:
            raise RuntimeError("BiLSTMModel must be fit before predict.")
        return np.full(len(x), self.classes_[int(np.argmax(self.priors_))])


def _tabular_to_sequence(x: np.ndarray, seq_len: int) -> np.ndarray:
    n_rows, n_features = x.shape
    step_width = int(np.ceil(n_features / seq_len))
    padded_width = step_width * seq_len
    if padded_width > n_features:
        x = np.pad(x, ((0, 0), (0, padded_width - n_features)), mode="constant")
    return x.reshape(n_rows, seq_len, step_width).astype(np.float32)


def _build_tiny_bilstm(input_dim: int, hidden_dim: int, n_classes: int):
    import torch
    from torch import nn

    class TinyBiLSTM(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True, bidirectional=True)
            self.head = nn.Linear(hidden_dim * 2, n_classes)

        def forward(self, x):
            _, (hidden, _) = self.lstm(x)
            both = torch.cat([hidden[-2], hidden[-1]], dim=1)
            return self.head(both)

    return TinyBiLSTM()
