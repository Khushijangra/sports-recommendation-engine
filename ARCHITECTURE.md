# SportMatch — Architecture Reference

## System Design Philosophy

SportMatch is built around three core design principles:

1. **Dual-engine cross-validation** — ML and rule-based engines run in parallel and verify each other
2. **Separation of concerns** — each pipeline stage (data, ranking, clustering, API) is independently runnable
3. **Zero-leakage evaluation** — all evaluation is student-level split, not row-level split

---

## Component Map

```
SportMatch/
├── src/data_pipeline/     ← Data ingestion and feature engineering
├── src/ranking/           ← Learning-to-Rank ML pipeline (primary)
├── src/clustering/        ← Unsupervised student segmentation
├── src/expert_system/     ← Rule-based recommendation engine
└── app/                   ← Flask REST API + web UI
```

---

## Data Flow

### Ingestion → Feature Engineering

```
data/students.csv  (raw fitness records)
         │
         ▼
src/data_pipeline/rebuild_dataset.py
         │
Phase 1  ├─ Load + Inspect
         │   detect nulls, dtype errors, out-of-range scores
         │
Phase 2  ├─ Structural Cleanup
         │   standardize column names, fix dtypes, drop duplicates
         │
Phase 3  ├─ Validation & Repair
         │   123 students had Age < 5 or null
         │   fix: map classname → expected age (Class 1 → 6, etc.)
         │   clip extreme BMI values to population median
         │
Phase 4  ├─ Encoding
         │   label encode: Gender, classname
         │   one-hot encode: sport names (20 sports → 20 columns)
         │
Phase 5  ├─ Normalization
         │   StandardScaler on all numeric features
         │   fit on train split only, transform val/test
         │
Phase 6  └─ Feature Engineering
             composite: StrengthScore = 0.6×Core + 0.4×UpperBody
             composite: EnduroAgilityScore = 0.5×Endurance + 0.5×Agility
             interaction: Speed×Agility, Core×Upper, Endurance×Speed
             percentile rank: each attribute vs. population
             height bands: short/normal/tall based on age-adjusted p-tiles
             BMI category: underweight/normal/overweight
             ─────────────────────────────────────────────────
             9 raw features → 75 engineered features
```

### Learning-to-Rank Pipeline

```
outputs/data_prepared.pkl  (75-feature dataset, 3,860 students)
         │
         ▼
src/ranking/prepare.py
         │
         ├─ Long-form expansion
         │   each student × 10 sports → 10 rows
         │   relevance = 10 - rank_index  (10=best, 1=worst)
         │   total: 38,600 rows × 75 features
         │
         ├─ Student-level split (NO ROW-LEVEL SPLIT)
         │   students_train: 70% of unique students
         │   students_val:   15% of unique students
         │   students_test:  15% of unique students
         │
         └─ outputs/data_prepared_rank.pkl

                    ▼
         src/ranking/train.py
         │   XGBRanker(objective='rank:ndcg')
         │   group_train = [10, 10, 10, ...]  ← 10 rows per student
         │   early stopping on val NDCG@10
         │   outputs: models/xgb_ranker.pkl
         │           outputs/ranking_metrics.json

                    ▼
         src/ranking/tune.py
         │   Optuna TPE sampler, 50 trials
         │   objective: maximize val NDCG@10
         │   outputs: models/xgb_ranker_tuned.pkl
         │           outputs/ranking_optimization_results.json

                    ▼
         src/ranking/promote.py
         │   copies tuned → models/xgb_ranker_production.pkl

                    ▼
         src/ranking/inference.py  (CLI)
             --input  features.csv
             --output recommendations.csv
             --k      10
```

### Expert System Pipeline

```
student fitness scores (runtime, no precomputed index)
         │
         ▼
src/expert_system/percentile_recommender.py
         │   compute P_j = PercentileRank(score_j, all N students)
         │   → converts raw 1–10 to 0–100 population percentile

                    ▼
src/expert_system/three_tier_recommender.py
         │
         ├─ Tier 1: Best Match Now
         │   for each of 20 sports:
         │       load weight profile from sport_profiles.py
         │       compute AsymmetricContribution(P_j, W_j) per attribute
         │       match_score = weighted_sum / total_weight × 10
         │   sort by match_score descending
         │   apply age filter (remove contraindicated sports)
         │   apply diversity filter (remove duplicate sport categories)
         │   → top 3 sports
         │
         ├─ Tier 2: Growth Potential
         │   for each sport not in Tier 1:
         │       for each weak attribute (score < 6) that sport needs (W ≥ 0.7):
         │           gain = (6 - score) × age_improvement_rate × W
         │       rank by total potential gain
         │   → top 3 sports with highest improvement ceiling
         │
         └─ Tier 3: Entry Sports
             select age-appropriate foundational sports
             with clear skill-transfer pathways (e.g., Athletics → Football)
             → top 3 entry points
```

### Clustering Pipeline

```
outputs/data_prepared.pkl  (same 75-feature dataset)
         │
         ▼
src/clustering/model.py
         │
         ├─ Preprocessing
         │   StandardScaler → PCA (retain 95% variance)
         │   fit on full dataset
         │
         ├─ Algorithm Search
         │   KMeans:  k in [2..15] → pick best composite score
         │   GMM:     k in [2..15] → pick best composite score
         │   DBSCAN:  eps × min_samples grid → pick best
         │
         │   Composite score = silhouette + 0.0001×CH - DB
         │
         ├─ Model Selection
         │   compare best KMeans vs best GMM vs best DBSCAN
         │   → winner: KMeans k=15 (silhouette=0.201, purity=81.8%)
         │
         └─ Stability Validation
             bootstrap n=20, subsample=80%
             refit winner model on each subsample
             ARI(original_labels, bootstrap_labels)
             → report mean_ari ± std_ari
```

### Web Application (Flask)

```
app/app.py
         │
         ├─ Startup
         │   load CSV (students.csv → fallback sample_students.csv)
         │   preprocess: normalize column names, fix Age, fix BMI
         │   instantiate ThreeTierRecommender(df)
         │
         ├─ GET /
         │   serve app/templates/index.html
         │
         ├─ GET /api/students/search?q=<query>
         │   filter df by name or class substring match
         │   return [{id, name, class, age, gender}, ...]
         │
         ├─ GET /api/recommend/<student_id>
         │   look up student row in df
         │   extract scores dict + age + height_pct
         │   call recommender.recommend(scores, age, height_pct, gender, prefs)
         │   build JSON: student info + 3-tier recommendations + scores + physical
         │   return JSON
         │
         ├─ GET /api/sports
         │   return all 20 sport profiles from sport_profiles.py
         │
         ├─ GET /api/stats
         │   aggregate stats: total students, schools, age range, gender split
         │
         └─ GET /api/methodology
             return algorithm description JSON
```

---

## Key Data Structures

### Long-Form Training DataFrame

```python
# 38,600 rows × (75 features + metadata)
{
    'student_id': str,       # group key for XGBRanker
    'rank_idx':   int,       # 0..9 (sport rank position)
    'relevance':  int,       # 10..1 (10=best, 1=worst) — training target
    'score':      float,     # expert system match score
    'sport_X':    float,     # one-hot sport indicator (20 columns)
    ... 75 engineered features ...
}

# Group structure (required for XGBRanker)
group_train = [10, 10, 10, ...]   # 10 sports per student
```

### Inference Input

```python
# Per-student, per-sport feature matrix
# For each new student (1 row of base features):
#   replicate 20 times, set sport_X OHE columns accordingly
# → 20 rows input → 20 scores output → argsort → top-K
```

### Expert System Recommendation Object

```python
{
    'tier1_best_match': [
        {'sport': str, 'score': float, 'reason': str},
        ...  # top 3
    ],
    'tier2_potential': [
        {'sport': str, 'improve_areas': [str], 'reason': str},
        ...  # top 3
    ],
    'tier3_entry': [
        {'sport': str, 'leads_to': [str]},
        ...  # top 3
    ]
}
```

---

## Model Files

| File | Size (approx) | Status |
|------|--------------|--------|
| `xgb_ranker.pkl` | ~2 MB | Generated by `train.py` |
| `xgb_ranker_tuned.pkl` | ~2 MB | Generated by `tune.py` |
| `xgb_ranker_production.pkl` | ~2 MB | Generated by `promote.py` |
| `kmeans_model.pkl` | ~150 KB | Generated by `clustering/run.py` |
| `clustering_pca.pkl` | ~2 KB | Generated with clustering |

> ⚠️ All model files are gitignored. Regenerate from source by running the pipeline.
> `rf_ranker.pkl` (~169 MB) exceeds GitHub's file size limit and is excluded permanently.

---

## Evaluation: NDCG@k Deep Dive

```
NDCG@k = DCG@k / IDCG@k

DCG@k  = Σ(i=1..k) (2^relevance_i - 1) / log2(i+1)
IDCG@k = DCG@k of perfect ranking

Example — student with ideal ranking [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]:
  Model predicts:   [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]  → NDCG@5 = 1.000
  Model predicts:   [ 9,10, 8, 7, 6, 5, 4, 3, 2, 1]  → NDCG@5 = 0.998 (almost perfect)
  Model predicts:   [ 1, 2, 3, 4,10, 9, 8, 7, 6, 5]  → NDCG@5 = 0.320 (poor)

Group-aware computation:
  Compute NDCG for each student group independently
  Report macro-average across all students
  → prevents large-group students from dominating the metric
```

---

## Scalability Notes

| Bottleneck | Current | Mitigation |
|-----------|---------|-----------|
| Training data size | 38,600 rows | Negligible for XGBoost; scales to 10M+ |
| Inference latency | ~50ms/student | Batch with 20 sport rows, vectorized |
| Clustering stability | O(n × k × iters) | Bootstrap subsample keeps this fast |
| Flask serving | Single-threaded | Swap for Gunicorn/uvicorn in production |
| PCA refit | One-time | Fitted object serialized in pkl |

---

## Technology Choices

| Decision | Choice | Alternatives Considered |
|----------|--------|------------------------|
| LTR framework | XGBoost | LightGBM (slower training), RankNet (slower inference) |
| HPO | Optuna | Grid search (too slow at 8D), Random (suboptimal) |
| Expert MCDM | TOPSIS | VIKOR, ELECTRE (more complex, less interpretable) |
| Normalization | Population percentile | Vector norm (scale-dependent), min-max (sensitive to outliers) |
| Web framework | Flask | FastAPI (heavier), Django (overkill for 5 endpoints) |
| Clustering | Auto-select composite | Fixed algorithm (introduces human bias) |
