<div align="center">

# 🏅 SportMatch
### Production ML Recommendation Engine — Sports Talent Identification

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![XGBoost](https://img.shields.io/badge/XGBoost-1.7%2B-FF6600?style=for-the-badge)](https://xgboost.readthedocs.io)
[![Optuna](https://img.shields.io/badge/Optuna-HPO-blue?style=for-the-badge)](https://optuna.org)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)

**A dual-engine recommendation system combining Learning-to-Rank ML with Multi-Criteria Decision Making — trained on 38,600 student–sport pairs across 20 sports.**

[Architecture](#-architecture) • [Results](#-results) • [ML Pipeline](#-ml-pipeline) • [API](#-api-design) • [Quick Start](#-quick-start) • [Engineering Decisions](#-engineering-decisions)

</div>

---

## 🎯 Problem & Solution

**Problem:** Physical education systems assign sports based on intuition or raw fitness scores without accounting for sport-specific physiological requirements, student age, or population-relative performance.

**Solution:** A two-engine recommendation system that:
1. **Learns ranked sport orderings from data** using XGBoost Learning-to-Rank (`rank:ndcg` objective)
2. **Generates interpretable, rule-driven recommendations** using a Modified TOPSIS decision framework with population percentile normalization
3. **Serves both engines via a REST API** deployable in any school information system

Both engines cross-validate each other. The ML engine provides data-driven precision; the expert engine provides explainability.

---

## 📊 Results

> All metrics evaluated on held-out test set — **15% of students, zero overlap with training data**.

### Learning-to-Rank Performance

| Model | NDCG@5 | NDCG@10 | MAP@10 | Hit@1 |
|-------|--------|---------|--------|-------|
| **XGBRanker (Tuned)** | **0.986** | **0.991** | **0.986** | **0.974** |
| Random Forest Baseline | 0.975 | 0.983 | 0.979 | 0.962 |
| Ordinal Regression Baseline | 0.750 | 0.762 | 0.750 | 0.650 |

> `NDCG@5 = 0.986` means the model's top-5 sport ordering is **98.6% as good as a perfect oracle ranking**.
> `Hit@1 = 0.974` means the **correct primary sport appears at rank 1 for 97.4% of students**.

### Per-Sport Breakdown

| Best Predicted (NDCG@5 = 1.0) | Hardest (NDCG@5) |
|-------------------------------|-----------------|
| Athletics, Swimming, Wrestling | Volleyball 0.957 · Hockey 0.959 · Football 0.965 |

> Team sports score lower due to overlapping physical profiles — a known challenge in multi-label sport recommendation.

### Hyperparameter Optimization (Optuna)

| Metric | Baseline | After 50-trial Optuna |
|--------|----------|----------------------|
| NDCG@5 | 0.975 | **0.986** (+1.1%) |
| Hit@1 | 0.962 | **0.974** (+1.2%) |

### Expert System Validation

| Test | Score | Method |
|------|-------|--------|
| Statistical Consistency | 100% | High vs. low attribute groups — 12/12 tests |
| Extreme Case Testing | 100% | Synthetic ideal-athlete profiles — 6/6 passed |
| Internal Consistency | 70.7% | Cluster-based recommendation stability |
| **Overall** | **92.7%** | Composite score |

### Clustering

| Metric | Value |
|--------|-------|
| Optimal k | 15 clusters |
| Algorithm | KMeans (wins via composite Silhouette/CH/DB scoring) |
| Cluster purity | 81.8% dominant-sport consistency |
| Stability (bootstrap ARI) | Computed across 20 iterations, 80% subsample |

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                       SportMatch System                              │
│                                                                      │
│   RAW DATA (9 fitness metrics, N students)                          │
│       │                                                              │
│       ▼                                                              │
│   ┌─────────────────────────────────────────┐                       │
│   │       DATA PIPELINE  (6 phases)         │                       │
│   │  Load → Clean → Validate → Encode →     │                       │
│   │  Normalize → Feature Engineering        │                       │
│   │  Output: 75 features per student        │                       │
│   └──────────────────┬──────────────────────┘                       │
│                      │                                               │
│         ┌────────────┴──────────────┐                               │
│         ▼                           ▼                               │
│  ┌──────────────────┐    ┌───────────────────────────┐              │
│  │   ML ENGINE      │    │   EXPERT ENGINE            │              │
│  │                  │    │                            │              │
│  │  Long-form build │    │  Modified TOPSIS           │              │
│  │  38,600 rows     │    │  Percentile Normalization  │              │
│  │  (student×sport) │    │  20 sport weight profiles  │              │
│  │       ↓          │    │  Age-appropriate filtering │              │
│  │  XGBRanker       │    │       ↓                    │              │
│  │  rank:ndcg       │    │  3-Tier Recommendations    │              │
│  │  Optuna 50 HPO   │    │  (Current/Growth/Entry)    │              │
│  │  NDCG@5=0.986    │    │  Validation: 92.7%         │              │
│  └──────┬───────────┘    └─────────────┬──────────────┘              │
│         │                              │                             │
│         └─────────────┬───────────────┘                             │
│                       ▼                                             │
│            ┌─────────────────────┐                                  │
│            │  CLUSTERING ENGINE  │                                   │
│            │  KMeans/GMM/DBSCAN  │                                   │
│            │  Auto model select  │                                   │
│            │  k=15, purity=81.8% │                                   │
│            └──────────┬──────────┘                                  │
│                       ▼                                             │
│            ┌─────────────────────┐                                  │
│            │   FLASK REST API    │                                   │
│            │  /api/recommend     │                                   │
│            │  /api/students      │                                   │
│            │  /api/sports        │                                   │
│            └─────────────────────┘                                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 ML Pipeline

### Step 1 — Data Preparation

```bash
python src/ranking/prepare.py
# Builds long-form training dataset: 38,600 rows × 75 features
# Train/Val/Test split: 70/15/15 — student-level (no leakage)
# Output: outputs/data_prepared_rank.pkl
```

**Long-form construction logic:**
```
Each student → 10 training rows (one per sport in ranked order)
Relevance score = 10 - rank_index   (10=best fit, 1=worst fit)
Group size per student = 10 (required for LTR group structure)
```

**Feature engineering (6 phases):**
```
Phase 1: Load + Inspect       → Detect nulls, dtypes, anomalies
Phase 2: Structural Cleanup   → Standardize column names, fix dtypes
Phase 3: Validation Repair    → Fix age/class mismatches (123 students)
Phase 4: Encoding             → Label encode + sport one-hot (20 sports)
Phase 5: Normalization        → StandardScaler on all numeric features
Phase 6: Engineering          → Composite scores, strength/endurance
                                interactions, percentile rank features,
                                height–weight ratios, BMI bands
→ 9 raw features → 75 engineered features
```

### Step 2 — Train Baseline

```bash
python src/ranking/train.py
# Output: models/xgb_ranker.pkl
#         outputs/ranking_metrics.json
```

```python
XGBRanker(
    objective      = 'rank:ndcg',
    eval_metric    = 'ndcg@10',
    learning_rate  = 0.08,
    max_depth      = 4,
    n_estimators   = 400,
    subsample      = 0.85,
    colsample_bytree = 0.85,
    min_child_weight = 6,
    reg_alpha      = 0.6,
    reg_lambda     = 2.0,
    random_state   = 42,
    n_jobs         = -1
)
```

### Step 3 — Hyperparameter Optimization

```bash
python src/ranking/tune.py
# 50-trial Bayesian search via Optuna
# Objective: maximize NDCG@10 on validation set
# Output: models/xgb_ranker_tuned.pkl
#         outputs/ranking_optimization_results.json
```

**Search space:**
```python
learning_rate    : log-uniform [0.03, 0.20]
max_depth        : int         [3, 7]
n_estimators     : int         [200, 600]
subsample        : float       [0.60, 0.95]
colsample_bytree : float       [0.60, 0.95]
min_child_weight : int         [3, 12]
reg_alpha        : float       [0.0, 1.5]
reg_lambda       : float       [0.5, 3.0]
```

### Step 4 — Promote & Serve

```bash
python src/ranking/promote.py
# Copies tuned → models/xgb_ranker_production.pkl

python src/ranking/inference.py \
  --input  data/sample_students.csv \
  --output outputs/top10_recommendations.csv \
  --k 10
```

---

## 🧠 Expert Engine: Modified TOPSIS

A rule-based recommendation engine that provides interpretable recommendations independent of the ML model — used for explainability and cross-validation.

### Why Two Engines?

| Concern | ML Engine | Expert Engine |
|---------|-----------|--------------|
| Accuracy | ✅ Highest (learned from data) | ✅ Strong (92.7% validated) |
| Explainability | ⚠️ SHAP required | ✅ Human-readable reasoning |
| New student (no training data) | ⚠️ Needs feature vector | ✅ Works immediately |
| Debugging recommendations | ⚠️ Complex | ✅ Traceable step-by-step |

Having both makes the system both **accurate and auditable**.

### Algorithm

```
INPUT: student fitness profile → {CoreStrength, UpperBody, Flexibility,
                                   Endurance, Speed, Agility} (scores 1–10)

STEP 1 — Percentile Transform
    For each attribute j:
        P_j = PercentileRank(student_score_j, all N students)
    → Converts raw 1–10 to 0–100 population-relative rank

STEP 2 — Weighted Match Score (per sport)
    For each of 20 sports with weight profile W:
        For each attribute j:
            contribution = AsymmetricFunction(P_j, W_j)
        match_score = (Σ W_j × contribution_j) / Σ W_j × 10

    AsymmetricFunction — thresholded, not linear:
        Critical (W ≥ 0.8): P≥70→1.0 | P≥50→0.7 | P≥30→0.4 | else→0.2
        Important (W ≥ 0.6): P≥60→0.9 | P≥40→0.6 | else→0.3
        Secondary (W < 0.6): linear 0.4 + (P/100)×0.4

STEP 3 — Age Filter
    Remove sports contraindicated for developmental stage:
    6–8 yrs:  exclude Boxing, Wrestling, Weightlifting, Judo
    9–11 yrs: exclude Boxing, Weightlifting
    12+ yrs:  all sports available

STEP 4 — Diversity Filter
    Prevent recommending redundant similar sports in top-3
    e.g., if Tennis ranked #1, Badminton moves down

OUTPUT — 3 Tiers:
    Tier 1: Best Match Now    → top-3 by current match score
    Tier 2: Growth Potential  → top-3 by improvement potential model
    Tier 3: Entry Sports      → age-appropriate foundational sports
```

**Why threshold-based, not linear?**
Real selection decisions are threshold-driven: a speed score in the 40th percentile vs. the 70th percentile is a qualitative difference for sprint sports, not just a marginal one. The asymmetric function models this correctly.

### Sport Weight Profiles

Each of 20 sports has a weight vector over 6 fitness attributes. Example:

| Sport | Core | Upper Body | Flex | Endurance | Speed | Agility |
|-------|------|-----------|------|-----------|-------|---------|
| Gymnastics | **0.95** | **0.95** | **0.95** | 0.55 | 0.70 | 0.90 |
| Athletics | 0.70 | 0.55 | 0.65 | **0.85** | **0.85** | 0.60 |
| Wrestling | **0.95** | 0.90 | 0.80 | 0.80 | 0.75 | 0.85 |
| Kho-Kho | 0.70 | 0.50 | 0.80 | 0.85 | **0.95** | **0.95** |
| Archery | 0.85 | 0.80 | 0.40 | 0.35 | 0.15 | 0.25 |

Full weight profiles and sport-specific references: [`src/expert_system/sport_profiles.py`](src/expert_system/sport_profiles.py)

---

## 🔗 Clustering Pipeline

```bash
python src/clustering/run.py
```

### Algorithm Selection

```python
# Search all three algorithms
best_kmeans = fit_kmeans_search(Xr, k_range=range(2, 16))
best_gmm    = fit_gmm_search(Xr, k_range=range(2, 16))
best_dbscan = fit_dbscan_grid(Xr, eps=[0.5, 1.0, 1.5], min_samples=[5, 10, 20])

# Composite scoring — select winner
score = silhouette + 0.0001 × calinski_harabasz - davies_bouldin

# → KMeans k=15 wins
```

### Stability Validation

```python
# 20-iteration bootstrap ARI — ensures clusters are stable, not random
for _ in range(20):
    subsample = random_sample(Xr, frac=0.80)
    refit model on subsample
    ari = adjusted_rand_score(original_labels[subsample], refitted_labels)
report: mean_ari ± std_ari
```

### Preprocessing

```
Raw features → StandardScaler → PCA (retain 95% variance) → clustering
PCA components computed once, reused for stability bootstrap
```

---

## 📐 Evaluation: Custom Metrics

All metrics in [`src/ranking/metrics.py`](src/ranking/metrics.py) are **group-aware** — computed per student, then averaged. This prevents large-group students from dominating the metric.

```python
def groupwise_eval(y, preds, groups):
    # For each student group (10 sports per student):
    #   NDCG@k  — measures if the right sports are ranked high
    #   MAP@k   — measures precision across top-k
    #   Hit@k   — binary: did correct sport appear in top-k?
    # Returns micro-average across all students
```

**Why not accuracy?**
With 20 sports, a random classifier achieves 5% accuracy. A model that ranks the right sport at position 2 instead of 1 looks like a complete failure under accuracy, but is near-perfect under NDCG. LTR metrics measure what actually matters: **is the recommendation list good?**

---

## 🌐 API Design

### Start the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Run with sample data (included)
python app/app.py
# → http://localhost:5000
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /` | — | Web UI |
| `GET /api/students/search?q=<query>` | — | Student lookup by name or class |
| `GET /api/recommend/<student_id>` | — | 3-tier recommendations for student |
| `GET /api/recommend/<id>?preferences=Swimming,Badminton` | — | Recommendations with sport preferences |
| `GET /api/sports` | — | All 20 sport profiles with weight vectors |
| `GET /api/stats` | — | Dataset statistics |
| `GET /api/methodology` | — | Algorithm description |

### Request / Response Example

```bash
curl http://localhost:5000/api/recommend/ANON_005
```

```json
{
  "student_id": "ANON_005",
  "age": 14,
  "gender": "M",
  "scores": {
    "CoreStrength": 9.0,
    "UpperBodyStrength": 8.7,
    "Flexibility": 7.1,
    "Endurance": 8.5,
    "Speed": 9.2,
    "Agility": 9.1,
    "Overall": 8.9
  },
  "physical": {
    "height_cm": 168.0,
    "weight_kg": 58.0,
    "bmi": 20.5
  },
  "recommendations": {
    "tier1_best_match": [
      {
        "sport": "Athletics",
        "score": 9.1,
        "reason": "Your speed (top 8%) matches Athletics requirements"
      },
      {
        "sport": "Kabaddi",
        "score": 8.8,
        "reason": "Your agility (top 9%) matches Kabaddi requirements"
      },
      {
        "sport": "Kho-Kho",
        "score": 8.6,
        "reason": "Exceptional speed and agility — core requirements for Kho-Kho"
      }
    ],
    "tier2_potential": [
      {
        "sport": "Gymnastics",
        "improve_areas": ["Flexibility"],
        "reason": "Work on Flexibility to unlock potential"
      }
    ],
    "tier3_entry": [
      {
        "sport": "Athletics",
        "leads_to": ["Football", "Hockey"]
      }
    ]
  }
}
```

---

## 📁 Project Structure

```
SportMatch/
│
├── README.md                       ← This file
├── ARCHITECTURE.md                 ← Deep system design
├── CHANGELOG.md                    ← Version history
├── CONTRIBUTING.md                 ← Contribution guide
├── SECURITY.md                     ← Security policy
├── LICENSE                         ← MIT
├── requirements.txt                ← Dependencies
├── .gitignore                      ← Protects data and model binaries
│
├── src/                            ← All Python source code
│   ├── ranking/                    ← Learning-to-Rank ML pipeline
│   │   ├── prepare.py              ← Long-form dataset builder
│   │   ├── train.py                ← XGBRanker training + evaluation
│   │   ├── tune.py                 ← Optuna hyperparameter optimization
│   │   ├── inference.py            ← Production inference CLI
│   │   ├── promote.py              ← Promote tuned → production
│   │   ├── ordinal.py              ← Ordinal regression baseline
│   │   └── metrics.py             ← Custom NDCG/MAP/Hit implementations
│   ├── clustering/
│   │   ├── model.py                ← KMeans/GMM/DBSCAN + stability
│   │   └── run.py                  ← CLI entry point
│   ├── data_pipeline/
│   │   └── rebuild_dataset.py      ← 6-phase data processing pipeline
│   └── expert_system/
│       ├── sport_profiles.py       ← 20-sport weight profile definitions
│       ├── three_tier_recommender.py ← Modified TOPSIS + 3-tier logic
│       ├── percentile_recommender.py ← Population percentile computation
│       └── preprocessing.py        ← Data cleaning utilities
│
├── app/
│   ├── app.py                      ← Flask REST API (5 endpoints)
│   ├── templates/index.html        ← Web UI
│   └── static/                     ← CSS + JS
│
├── data/
│   ├── sample_students.csv         ← 100-row anonymized sample (PUBLIC)
│   └── README.md                   ← Dataset schema + privacy notice
│
├── models/                         ← Trained models (excluded from repo)
│   └── README.md                   ← Model cards + training instructions
│
├── outputs/
│   ├── ranking_metrics.json        ← Baseline model evaluation
│   ├── ranking_metrics_tuned.json  ← Post-Optuna evaluation
│   ├── ranking_optimization_results.json ← Best hyperparameters
│   ├── clustering_optimal_k.json   ← Cluster selection result
│   ├── clustering_validation.json  ← Algorithm comparison
│   └── plots_showcase/             ← Visualizations
│       ├── model_comparison.png
│       ├── ndcg_curve.png
│       ├── per_sport_heatmap.png
│       └── cluster_distribution.png
│
├── notebooks/
│   └── EndToEnd_RF_KMeans_XGBoost.ipynb ← End-to-end exploration
│
└── scripts/
    └── check_before_push.py        ← Pre-push safety validator
```

---

## ⚙️ Engineering Decisions

### Why Learning-to-Rank over Classification?

| Approach | Issue |
|---------|-------|
| Multi-class (predict 1 sport) | Loses ordinal information — rank 2 treated same as rank 20 |
| Multi-label (predict many) | Doesn't capture relative preference between sports |
| **Learning-to-Rank** | ✅ Models the full ranking — evaluated correctly with NDCG/MAP |

XGBRanker with `rank:ndcg` directly optimizes for ranking quality, not accuracy — which is what a recommendation system actually needs.

### Why Student-Level Train/Test Split?

A naive row-level split (splitting among 38,600 rows) would leak information:
- The same student's features appear in both train and test
- The model memorizes student profiles, not sport-fitness relationships

Student-level split (70% of students train, 15% val, 15% test) ensures **zero leakage**:
```python
students_train, students_temp = train_test_split(students, test_size=0.30)
students_val, students_test   = train_test_split(students_temp, test_size=0.50)
```

### Why Percentile Normalization over Raw Scores?

A raw speed score of 6/10 means different things if:
- 80% of students score below 6 → above average
- 20% of students score below 6 → below average

Population percentile transformation gives the score meaning relative to the actual student population. This is standard practice in talent assessment systems.

### Why Thresholded Contribution, not Linear Distance?

Threshold-based selection mirrors how real selection works: being in the top-30% vs. top-70% for a critical attribute is a qualitative difference, not a marginal one. Linear distance functions underweight this effect. The asymmetric step function models the non-linearity correctly.

### Why Three Clustering Algorithms?

Different datasets favor different cluster geometries:
- **KMeans**: Spherical clusters, fast
- **GMM**: Elliptical clusters, soft assignments
- **DBSCAN**: Arbitrary shapes, handles noise

Automated composite scoring selects the winner — removes human bias from the choice.

---

## 🚀 Quick Start

### Option A — Run with Sample Data (immediate)

```bash
git clone https://github.com/YOUR_USERNAME/SportMatch.git
cd SportMatch
pip install -r requirements.txt

python app/app.py
# → http://localhost:5000
```

The app auto-detects `data/sample_students.csv` (100 students, included).

### Option B — Full Pipeline (requires your dataset)

```bash
# 1. Place your dataset in data/ (schema: see data/README.md)

# 2. Build training data
python src/ranking/prepare.py

# 3. Train baseline
python src/ranking/train.py

# 4. Optimize hyperparameters
python src/ranking/tune.py

# 5. Promote to production
python src/ranking/promote.py

# 6. Run clustering
python src/clustering/run.py

# 7. Inference on new data
python src/ranking/inference.py \
  --input  data/your_students.csv \
  --output outputs/recommendations.csv \
  --k 10
```

### Environment

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate        # Linux/Mac
pip install -r requirements.txt
```

---

## 📦 Dataset

> ⚠️ The full dataset is **not included** — it contains real student fitness records subject to institutional data governance.

A **100-row anonymized sample** (`data/sample_students.csv`) is included for:
- Running the Flask app
- Testing the pipeline
- Verifying inference output

### Schema

| Column | Type | Description |
|--------|------|-------------|
| `student_id` | str | Anonymized ID |
| `Age` | int | 6–18 years |
| `Gender` | str | M / F |
| `classname` | str | Class 1–12 |
| `CoreStrengthScore` | float | 1–10 (trunk stability) |
| `UpperBodyStrengthScore` | float | 1–10 (push-up/grip) |
| `FlexibilityScore` | float | 1–10 (ROM test) |
| `EnduranceScore` | float | 1–10 (beep test proxy) |
| `SpeedScore` | float | 1–10 (sprint, time-converted) |
| `AgilityScore` | float | 1–10 (T-test / shuttle) |
| `OverallScore` | float | 1–10 (composite) |
| `Height_cm` | float | Height in cm |
| `Weight_kg` | float | Weight in kg |
| `BMI` | float | Calculated |

Full dataset: **3,860 students × 14 base columns → 75 engineered features**

---

## 🔑 Feature Importance

Top features from SHAP analysis on the tuned XGBRanker:

| Rank | Feature | Gain | Interpretation |
|------|---------|------|----------------|
| 1 | CoreStrengthScore (f43) | 87.3 | Dominant predictor — relevant to 18/20 sports |
| 2 | StrengthScore (composite) | 25.8 | Engineered from Core + Upper Body |
| 3 | f47 (interaction) | 22.3 | Speed × Agility cross-feature |
| 7 | Weight_kg | 14.3 | Key for strength sports and body composition |
| 10 | BMI | 8.7 | Relevant for gymnastics and endurance sports |

**SHAP findings:**
- CoreStrength and SpeedScore have highest positive SHAP values for top-rank sports
- Endurance and Agility strongly drive Athletics and Football recommendations
- Height × Weight interaction features contribute meaningfully to body-type-sensitive sports (Gymnastics, Basketball, Weightlifting)
- Fairness-normalized features: gender bias < 2% NDCG difference across demographic groups

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| ML Framework | XGBoost ≥ 1.7 |
| Hyperparameter Optimization | Optuna ≥ 3.4 |
| Data Processing | Pandas ≥ 2.0, NumPy ≥ 1.24 |
| Statistical | SciPy ≥ 1.11 |
| Clustering | scikit-learn ≥ 1.3 |
| Explainability | SHAP ≥ 0.44 |
| Web Framework | Flask ≥ 3.0 |
| Visualization | Matplotlib ≥ 3.7, Seaborn ≥ 0.12 |
| Language | Python 3.10+ |

---

## 🛣 Future Work

- [ ] **Online learning**: Update model as new fitness assessments arrive each semester
- [ ] **GNN-based ranking**: Model sport similarity as a graph for improved ranking
- [ ] **Multi-label extension**: Students with dual-sport potential
- [ ] **Mobile API**: React Native frontend for tablet-based school deployment
- [ ] **A/B testing framework**: Compare ML engine vs. expert engine recommendations longitudinally
- [ ] **Physiological device integration**: Direct import from fitness tracker APIs

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
git clone https://github.com/YOUR_USERNAME/SportMatch.git
cd SportMatch && pip install -r requirements.txt
```

---

## 📄 License

MIT — see [LICENSE](LICENSE).

> Dataset not included. Only anonymized sample data (`data/sample_students.csv`) is distributed under this license.

---

<div align="center">
<b>SportMatch</b> · XGBRanker · Learning-to-Rank · Modified TOPSIS · Flask
</div>
