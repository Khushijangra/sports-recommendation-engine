import numpy as np
from typing import List, Dict


def ndcg_at_k(y_true: np.ndarray, y_score: np.ndarray, k: int) -> float:
    order = np.argsort(-y_score)
    y_true_sorted = y_true[order][:k]
    gains = (2**y_true_sorted - 1)
    discounts = 1 / np.log2(np.arange(2, k + 2))
    dcg = np.sum(gains * discounts)
    ideal_order = np.argsort(-y_true)
    ideal_sorted = y_true[ideal_order][:k]
    ideal_gains = (2**ideal_sorted - 1)
    ideal_dcg = np.sum(ideal_gains * discounts)
    return float(dcg / ideal_dcg) if ideal_dcg > 0 else 0.0


def apk(y_true_binary: np.ndarray, y_score: np.ndarray, k: int) -> float:
    order = np.argsort(-y_score)[:k]
    hits = y_true_binary[order] > 0
    if not np.any(hits):
        return 0.0
    precisions = []
    hit_count = 0
    for i, is_hit in enumerate(hits, start=1):
        if is_hit:
            hit_count += 1
            precisions.append(hit_count / i)
    return float(np.mean(precisions)) if precisions else 0.0


def hit_at_k(y_true_binary: np.ndarray, y_score: np.ndarray, k: int) -> float:
    order = np.argsort(-y_score)[:k]
    hits = y_true_binary[order] > 0
    return float(1.0 if np.any(hits) else 0.0)


def groupwise_eval(y: np.ndarray, preds: np.ndarray, groups: List[int]) -> Dict[str, float]:
    metrics = {'ndcg@1': [], 'ndcg@3': [], 'ndcg@5': [], 'ndcg@10': [], 'map@10': [], 'hit@1': []}
    idx = 0
    for g in groups:
        yt = y[idx: idx + g]
        ps = preds[idx: idx + g]
        metrics['ndcg@1'].append(ndcg_at_k(yt, ps, 1))
        metrics['ndcg@3'].append(ndcg_at_k(yt, ps, min(3, g)))
        metrics['ndcg@5'].append(ndcg_at_k(yt, ps, min(5, g)))
        metrics['ndcg@10'].append(ndcg_at_k(yt, ps, min(10, g)))
        ybin = (yt == yt.max()).astype(int)
        metrics['map@10'].append(apk(ybin, ps, min(10, g)))
        metrics['hit@1'].append(hit_at_k(ybin, ps, 1))
        idx += g
    return {k: float(np.mean(v)) if len(v) > 0 else 0.0 for k, v in metrics.items()}


