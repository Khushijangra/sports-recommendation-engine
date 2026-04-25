# Changelog

All notable changes to SportMatch are documented here.

---

## [1.0.0] — 2026-06

### Added — Learning-to-Rank Pipeline

- XGBRanker with `rank:ndcg` objective trained on 38,600 student–sport pairs
- Long-form dataset construction (10 sports × N students, with relevance labels)
- Student-level train/val/test split (70/15/15) — zero leakage
- 50-trial Optuna Bayesian hyperparameter optimization
- Custom group-aware evaluation: NDCG@k, MAP@k, Hit@k (`src/ranking/metrics.py`)
- Random Forest and Ordinal Regression baselines for comparison
- Model promotion workflow: baseline → tuned → production
- CLI inference script with configurable top-K output

### Added — Expert Recommendation Engine

- Modified TOPSIS with population percentile normalization
- Asymmetric threshold-based contribution functions (models real selection thresholds)
- 20 sport weight profiles derived from sports physiology literature
- 3-tier recommendation architecture (Best Match / Growth Potential / Entry Sports)
- Age-appropriate filtering with developmental stage constraints
- Tier 2 growth model using age-specific attribute improvement rates
- Diversity filter to avoid recommending similar sports in top-3
- Human-readable reason generation for every recommendation

### Added — Clustering Pipeline

- Multi-algorithm search: KMeans, GMM, DBSCAN
- Automated winner selection via composite Silhouette / CH / Davies-Bouldin scoring
- Bootstrap stability validation (ARI over 20 iterations, 80% subsample)
- Cluster profiling with dominant-sport purity analysis
- Result: KMeans k=15, silhouette=0.201, purity=81.8%

### Added — Data Pipeline

- 6-phase processing pipeline: Load → Clean → Validate → Encode → Normalize → Engineer
- Age correction for 123 students with class-to-age mapping
- BMI outlier detection and median substitution
- 75 engineered features from 9 raw fitness inputs
- Composite scores, interaction terms, percentile rank features, height bands

### Added — Web Application

- Flask REST API with 5 endpoints
- Auto-detects full dataset or falls back to anonymized sample
- JSON responses with 3-tier recommendations + raw scores + physical attributes
- Preference-aware recommendations (query param filtering)

### Added — Engineering

- `.gitignore` protecting student data, model binaries, dev artifacts
- Pre-push safety validator (`scripts/check_before_push.py`)
- 100-row fully anonymized sample dataset for reproducibility
- `outputs/` directory with all evaluation JSON artifacts
- `models/README.md` with model cards and training instructions
