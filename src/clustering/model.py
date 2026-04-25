"""
Improved clustering pipeline with model selection, validation, stability, and profiling.
Uses prepared clustering features from outputs/data_prepared.pkl (Phase 1 artifacts).
Exports:
  - outputs/clustering_optimal_model.json
  - outputs/clustering_validation.json
  - outputs/clustering_stability.json
  - outputs/cluster_profiles.json
  - outputs/cluster_characteristics.json
  - outputs/plots/clustering_pca_2d.png
"""

import os
import json
import pickle
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, DBSCAN
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score, adjusted_rand_score
import matplotlib.pyplot as plt


@dataclass
class ClusterResult:
    algo: str
    params: Dict[str, Any]
    labels: np.ndarray
    metrics: Dict[str, float]


def ensure_dirs():
    os.makedirs('outputs', exist_ok=True)
    os.makedirs('outputs/plots', exist_ok=True)


def load_clustering_data() -> Tuple[pd.DataFrame, List[str]]:
    with open('outputs/data_prepared.pkl', 'rb') as f:
        data = pickle.load(f)
    X = data.get('X_train_clustering')
    if X is None:
        # fallback to supervised features numeric if needed
        X = data['X_train_supervised'].select_dtypes(include=[np.number])
    features = list(X.columns)
    return X, features


def preprocess(X: pd.DataFrame, pca_var: float = 0.95, max_components: int = 50) -> Tuple[np.ndarray, PCA, StandardScaler]:
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X.values)
    pca = PCA(n_components=min(max_components, Xs.shape[1]))
    Xp = pca.fit_transform(Xs)
    # reduce to target explained variance
    cumsum = np.cumsum(pca.explained_variance_ratio_)
    k = np.searchsorted(cumsum, pca_var) + 1
    Xr = Xp[:, :k]
    return Xr, pca, scaler


def evaluate_internal(Xr: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
    # guard invalid labels
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    res = {'n_clusters': float(n_clusters)}
    if n_clusters <= 1:
        res.update({'silhouette': -1.0, 'calinski_harabasz': -1.0, 'davies_bouldin': np.inf})
        return res
    res['silhouette'] = float(silhouette_score(Xr, labels))
    res['calinski_harabasz'] = float(calinski_harabasz_score(Xr, labels))
    res['davies_bouldin'] = float(davies_bouldin_score(Xr, labels))
    return res


def fit_kmeans_search(Xr: np.ndarray, k_range: range) -> ClusterResult:
    best: Optional[ClusterResult] = None
    for k in k_range:
        km = KMeans(n_clusters=k, n_init='auto', random_state=42)
        labels = km.fit_predict(Xr)
        metrics = evaluate_internal(Xr, labels)
        cand = ClusterResult(algo='kmeans', params={'n_clusters': k}, labels=labels, metrics=metrics)
        if best is None or _is_better(cand.metrics, best.metrics):
            best = cand
    return best


def fit_gmm_search(Xr: np.ndarray, k_range: range) -> ClusterResult:
    best: Optional[ClusterResult] = None
    for k in k_range:
        gmm = GaussianMixture(n_components=k, covariance_type='full', random_state=42)
        labels = gmm.fit_predict(Xr)
        metrics = evaluate_internal(Xr, labels)
        cand = ClusterResult(algo='gmm', params={'n_components': k, 'covariance_type': 'full'}, labels=labels, metrics=metrics)
        if best is None or _is_better(cand.metrics, best.metrics):
            best = cand
    return best


def fit_dbscan_grid(Xr: np.ndarray, eps_list: List[float], min_samples_list: List[int]) -> ClusterResult:
    best: Optional[ClusterResult] = None
    for eps in eps_list:
        for ms in min_samples_list:
            db = DBSCAN(eps=eps, min_samples=ms, n_jobs=-1)
            labels = db.fit_predict(Xr)
            metrics = evaluate_internal(Xr, labels)
            cand = ClusterResult(algo='dbscan', params={'eps': eps, 'min_samples': ms}, labels=labels, metrics=metrics)
            if best is None or _is_better(cand.metrics, best.metrics):
                best = cand
    return best


def _is_better(m1: Dict[str, float], m2: Dict[str, float]) -> bool:
    # Composite: maximize silhouette, CH; minimize DB
    s1 = m1.get('silhouette', -1.0)
    ch1 = m1.get('calinski_harabasz', -1.0)
    db1 = m1.get('davies_bouldin', np.inf)
    s2 = m2.get('silhouette', -1.0)
    ch2 = m2.get('calinski_harabasz', -1.0)
    db2 = m2.get('davies_bouldin', np.inf)
    score1 = s1 + 0.0001 * ch1 - db1  # scaled composite
    score2 = s2 + 0.0001 * ch2 - db2
    return score1 > score2


def stability_bootstrap_ari(Xr: np.ndarray, base_labels: np.ndarray, algo: str, params: Dict[str, Any], n_iter: int = 20, frac: float = 0.8) -> Dict[str, float]:
    aris = []
    rng = np.random.RandomState(42)
    n = Xr.shape[0]
    for _ in range(n_iter):
        idx = rng.choice(n, size=int(frac * n), replace=False)
        Xb = Xr[idx]
        if algo == 'kmeans':
            km = KMeans(n_clusters=params['n_clusters'], n_init='auto', random_state=42)
            km.fit(Xb)
            # predict base subset labels using fitted model
            lb = km.predict(Xr[idx])
        elif algo == 'gmm':
            gmm = GaussianMixture(n_components=params['n_components'], covariance_type='full', random_state=42)
            gmm.fit(Xb)
            lb = gmm.predict(Xr[idx])
        else:
            # not supported for DBSCAN (no predict)
            continue
        aris.append(adjusted_rand_score(base_labels[idx], lb))
    return {
        'n_bootstrap': float(len(aris)),
        'ari_mean': float(np.mean(aris)) if aris else 0.0,
        'ari_std': float(np.std(aris)) if aris else 0.0
    }


def cluster_profiles(X: pd.DataFrame, labels: np.ndarray) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    df = X.copy()
    df['cluster'] = labels
    profiles = {}
    characteristics = {}
    for cl in sorted(df['cluster'].unique()):
        group = df[df['cluster'] == cl].drop(columns=['cluster'])
        profiles[str(cl)] = {
            'count': int(len(group)),
            'means': group.mean(numeric_only=True).round(3).to_dict(),
            'stds': group.std(numeric_only=True).round(3).to_dict(),
            'medians': group.median(numeric_only=True).round(3).to_dict()
        }
    # Most distinguishing features by ANOVA-like ratio (between/within as proxy)
    # Simple heuristic: std of cluster means divided by global std
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c != 'cluster']
    global_std = df[numeric_cols].std().replace(0, np.nan)
    means_by_cluster = df.groupby('cluster')[numeric_cols].mean()
    dispersion = means_by_cluster.std() / global_std
    top_features = dispersion.sort_values(ascending=False).head(15).replace([np.inf, -np.inf], np.nan).dropna().round(3).to_dict()
    characteristics['top_distinguishing_features'] = top_features
    return profiles, characteristics


def plot_pca(Xr: np.ndarray, labels: np.ndarray):
    plt.figure(figsize=(8, 6))
    # already PCA space; plot first two components
    x = Xr[:, 0]
    y = Xr[:, 1] if Xr.shape[1] > 1 else np.zeros_like(x)
    scatter = plt.scatter(x, y, c=labels, cmap='tab10', s=12, alpha=0.8)
    plt.xlabel('PC1')
    plt.ylabel('PC2')
    plt.title('Clustering (PCA space)')
    plt.colorbar(scatter, label='cluster')
    plt.tight_layout()
    plt.savefig('outputs/plots/clustering_pca_2d.png', dpi=300, bbox_inches='tight')
    plt.close()


def main():
    ensure_dirs()
    # Load and preprocess
    X, feat_names = load_clustering_data()
    Xr, pca, scaler = preprocess(X)

    # Search models
    k_range = range(2, min(16, max(3, Xr.shape[1] + 1)))
    best_kmeans = fit_kmeans_search(Xr, k_range)
    best_gmm = fit_gmm_search(Xr, k_range)
    best_dbscan = fit_dbscan_grid(Xr, eps_list=[0.5, 1.0, 1.5], min_samples_list=[5, 10, 20])

    # Select global best
    candidates = [best_kmeans, best_gmm, best_dbscan]
    best = candidates[0]
    for cand in candidates[1:]:
        if _is_better(cand.metrics, best.metrics):
            best = cand

    # Stability (for centroidal models)
    stability = stability_bootstrap_ari(Xr, best.labels, best.algo, best.params, n_iter=20, frac=0.8)

    # Profiles
    profiles, characteristics = cluster_profiles(X, best.labels)

    # Plot
    plot_pca(Xr, best.labels)

    # Save
    with open('outputs/clustering_optimal_model.json', 'w') as f:
        json.dump({
            'algorithm': best.algo,
            'params': best.params,
            'metrics': best.metrics,
            'pca_components': int(Xr.shape[1])
        }, f, indent=2)

    with open('outputs/clustering_validation.json', 'w') as f:
        json.dump({
            'kmeans': best_kmeans.metrics,
            'gmm': best_gmm.metrics,
            'dbscan': best_dbscan.metrics
        }, f, indent=2)

    with open('outputs/clustering_stability.json', 'w') as f:
        json.dump(stability, f, indent=2)

    with open('outputs/cluster_profiles.json', 'w') as f:
        json.dump(profiles, f, indent=2)

    with open('outputs/cluster_characteristics.json', 'w') as f:
        json.dump(characteristics, f, indent=2)

    print("[OK] Clustering completed. See outputs/clustering_optimal_model.json and plots.")


if __name__ == '__main__':
    main()


