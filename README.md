# 🏅 Explainable Youth Sports Recommendation Using Asymmetric Contribution Scoring (ACS)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Conference](https://img.shields.io/badge/Springer-LNCS-003366?style=for-the-badge)](https://www.springer.com/gp/computer-science/lncs)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Status: Reproducible](https://img.shields.io/badge/Reproducibility-Verified-22c55e?style=for-the-badge)]()

> **Official Implementation Repository for the Research Paper:**  
> *"Explainable Youth Sports Recommendation Using Asymmetric Contribution Scoring"*  
> **Authors:** Jatin Sheoran, Khushi Jangra, Dr. Tapas Badal  
> **Affiliation:** Department of Computer Science & Engineering, Bennett University, Greater Noida, India  
> **Target Venue:** Springer Lecture Notes in Computer Science (LNCS) Proceedings  

---

## 📌 Table of Contents
- [Overview & Research Motivation](#-overview--research-motivation)
- [Methodology & Architecture](#-methodology--architecture)
  - [1. Cluster-Based Baseline (First Implementation)](#1-cluster-based-baseline-first-implementation)
  - [2. Proposed Asymmetric Contribution Scoring (ACS)](#2-proposed-asymmetric-contribution-scoring-acs)
  - [3. Three-Tier Recommendation Architecture](#3-three-tier-recommendation-architecture)
  - [4. LTAD-Aligned Age Filtering](#4-ltad-aligned-age-filtering)
- [Complete 20 × 6 Sport-Profile Weight Matrix](#-complete-20--6-sport-profile-weight-matrix)
- [Experimental Results & Validation](#-experimental-results--validation)
  - [ACS Validation Across 6 Dimensions](#acs-validation-across-6-dimensions)
  - [Comparison with Standard TOPSIS](#comparison-with-standard-topsis)
  - [Granular Explainability Comparison](#granular-explainability-comparison)
- [Project Structure & Mapping to Paper](#-project-structure--mapping-to-paper)
- [Quick Start & Reproducibility](#-quick-start--reproducibility)
- [Scope & Limitations](#-scope--limitations)
- [Citation](#-citation)
- [License](#-license)

---

## 🎯 Overview & Research Motivation

Matching young athletes with developmentally appropriate sports disciplines is a fundamental challenge in physical education and youth talent identification. Traditional school sports assignment relies heavily on parental preference, subjective coach intuition, or unweighted fitness totals, leading to athlete dropout, unfulfilled potential, and injury risks.

This repository provides the complete, reproducible codebase for our study of **3,818 students (ages 5–18) from 11 schools across 20 sports disciplines**. 

The research traces the systematic evolution from an unsupervised **K-Means cluster-based affinity scoring baseline** ($k=6$, 12 engineered traits) to **Asymmetric Contribution Scoring (ACS)**—a transparent Multi-Criteria Decision Making (MCDM) framework designed for intrinsic explainability and developmental alignment.

```
Raw Fitness Measurements (SAI Protocol)
                 │
                 ▼
    Percentile Normalization (P_ij) ──► Relative Standing (0–100)
                 │
                 ▼
   Stepped Contribution Function f(P_ij, w_sj) ◄── 20 × 6 Sport Weights
                 │
                 ▼
      Composite Score C_is (Scale 0–10)
                 │
                 ▼
  Three-Tier Recommendation + LTAD Age Safety Filter
  ├── Tier 1: Best Match (Current Ability Match + Diversity)
  ├── Tier 2: Growth Potential (High-Ceiling Development Targets)
  └── Tier 3: Entry Sports (Age-Appropriate Foundational Sports)
```

---

## 🔬 Methodology & Architecture

### 1. Cluster-Based Baseline (First Implementation)
* **Feature Space:** 12 composite traits engineered from raw physiological tests via $z$-score normalization (e.g., `power_trait`, `strength_to_weight`, `endurance_trait`).
* **Clustering:** K-Means with Lloyd's algorithm ($k=6$, $n\_init=10$, fixed seed 42).
* **Metrics:** Silhouette Score = **0.177**, Davies-Bouldin Index = **1.520**, Calinski-Harabasz = **894.79**.
* **Identified Limitations:** Hard cluster boundaries, cluster-level rather than individual-level explainability (65% of score dictated by cluster centroid), manually calibrated penalty multipliers, and post-hoc diversification constraints (20% cap) required to prevent distribution collapse.

### 2. Proposed Asymmetric Contribution Scoring (ACS)
ACS addresses each baseline limitation directly:
1. **Population-Wide Percentile Normalization:**
   $$P_{ij} = \frac{\text{rank}(x_{ij})}{N} \times 100$$
   Mitigates skew and non-normal test distributions without distorting ordinal ranks.
2. **Stepped Asymmetric Contribution Function $f(P_{ij}, w_{sj})$:**
   A non-linear mapping reflecting physiological demand thresholds:
   * **Critical Attributes ($w_{sj} \geq 0.85$):** 4 discrete steps ($\ge 85 \to 1.0$, $\ge 70 \to 0.7$, $\ge 50 \to 0.3$, $< 50 \to 0.0$). Deficiencies severely penalized; provides natural noise absorption.
   * **Important Attributes ($0.65 \le w_{sj} < 0.85$):** 3 steps ($\ge 75 \to 1.0$, $\ge 50 \to 0.6$, $< 50 \to 0.2$).
   * **Minor Attributes ($w_{sj} < 0.65$):** Linear interpolation for smooth scoring ($0.2 \to 1.0$).
3. **Composite Scoring:**
   $$C_{is} = \frac{\sum_{j=1}^{6} w_{sj} \cdot f(P_{ij}, w_{sj})}{\sum_{j=1}^{6} w_{sj}} \times 10$$

### 3. Three-Tier Recommendation Architecture
Aligned with Long-Term Athlete Development (LTAD) principles:
* **Tier 1 (Best Match):** Top 3 sports by current composite score, filtered for age appropriateness and discipline diversity (prevents recommending three identical combat or racket sports).
* **Tier 2 (Growth Potential):** Sports where the student is one developmental leap away from an elite fit (identifies high-ceiling growth opportunities).
* **Tier 3 (Entry Sports):** Foundational, low-barrier disciplines prioritizing broad motor skill acquisition and participation.

### 4. LTAD-Aligned Age Filtering
* **Ages 6–8 (Early Childhood):** 7 eligible foundational sports (Swimming, Gymnastics, Athletics, Football, Badminton, Table Tennis, Kho-Kho). High-impact collision and heavy-load disciplines restricted.
* **Ages 9–11 (Late Childhood):** 15 eligible sports (combat sparring and maximum weightlifting restricted).
* **Ages 12–18 (Adolescence):** All 20 sports eligible.

---

## 📋 Complete 20 × 6 Sport-Profile Weight Matrix

The complete, evidence-based physiological requirement matrix across all 20 sports and 6 direct attributes (Table 5 in paper), derived from sports science literature and expert calibration:

| Sport | Category | Core Strength | Upper Body | Flexibility | Endurance | Speed | Agility |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Archery** | Precision | 0.85 | 0.80 | 0.40 | 0.35 | 0.15 | 0.25 |
| **Shooting** | Precision | 0.75 | 0.65 | 0.25 | 0.30 | 0.10 | 0.15 |
| **Athletics** | Endurance / Track | 0.70 | 0.55 | 0.65 | 0.85 | 0.85 | 0.60 |
| **Cycling** | Endurance | 0.75 | 0.45 | 0.55 | 0.95 | 0.65 | 0.35 |
| **Swimming** | Endurance | 0.85 | 0.90 | 0.85 | 0.85 | 0.70 | 0.55 |
| **Football** | Team Field | 0.75 | 0.55 | 0.65 | 0.85 | 0.85 | 0.85 |
| **Hockey** | Team Field | 0.75 | 0.70 | 0.60 | 0.85 | 0.80 | 0.80 |
| **Basketball** | Team Court | 0.70 | 0.70 | 0.55 | 0.75 | 0.80 | 0.85 |
| **Volleyball** | Team Court | 0.70 | 0.75 | 0.65 | 0.65 | 0.70 | 0.80 |
| **Badminton** | Racket | 0.65 | 0.70 | 0.75 | 0.70 | 0.85 | 0.90 |
| **Table Tennis** | Racket | 0.55 | 0.60 | 0.65 | 0.55 | 0.80 | 0.90 |
| **Tennis** | Racket | 0.75 | 0.80 | 0.70 | 0.80 | 0.80 | 0.85 |
| **Boxing** | Combat | 0.90 | 0.90 | 0.55 | 0.85 | 0.85 | 0.80 |
| **Wrestling** | Combat | 0.95 | 0.90 | 0.80 | 0.80 | 0.75 | 0.85 |
| **Judo** | Combat | 0.90 | 0.85 | 0.85 | 0.75 | 0.75 | 0.85 |
| **Gymnastics** | Artistic | 0.95 | 0.95 | 0.95 | 0.55 | 0.70 | 0.90 |
| **Fencing** | Combat | 0.70 | 0.70 | 0.80 | 0.65 | 0.90 | 0.90 |
| **Kabaddi** | Traditional | 0.85 | 0.80 | 0.70 | 0.85 | 0.80 | 0.90 |
| **Kho-Kho** | Traditional | 0.70 | 0.50 | 0.80 | 0.85 | 0.95 | 0.95 |
| **Weightlifting** | Strength | 0.95 | 0.95 | 0.75 | 0.40 | 0.70 | 0.45 |

*Source code location:* [`src/expert_system/sport_profiles.py`](src/expert_system/sport_profiles.py)

---

## 📊 Experimental Results & Validation

### ACS Validation Across 6 Dimensions
All reported metrics represent **internal validation** on the evaluated dataset of 3,818 students:

| Dimension | Evaluation Test | Result | Paper Reference |
|:---|:---|:---:|:---:|
| **Monotonicity** | Increase any attribute $\to$ score non-decreasing | **100%** (36,000 tests) | Table 8 |
| **Cross-Fold Stability** | 5-fold cross-validation on percentiles | **92.2% $\pm$ 1.1%** | Table 8 |
| **Weight Robustness** | $\pm$20% perturbation across all 120 weights | **0% Top-1 Change** | Table 8 |
| **Percentile Necessity** | Ablation test: raw scores vs. percentiles | **68% Top-1 Changed** | Table 8 |
| **Age Safety** | Ablation test: removing age filter ($<12$ yrs) | **54.7%** combat sports avoided | Table 8 |
| **Diversity Impact** | Ablation test: removing diversity filter | **0% Top-1, 31.6% Top-3** | Table 8 |

### Comparison with Standard TOPSIS
Benchmarked on the same 3,818 student population using identical attribute weights:

| Evaluation Metric | ACS (Proposed) | Standard TOPSIS | Takeaway |
|:---|:---:|:---:|:---|
| **Gini Concentration** | **0.518** | 0.642 | Lower concentration across sports |
| **Top-1 Agreement** | 37.2% (Top-1 overlap) | — | Substantial ranking differences |
| **Kendall's $\tau$ Correlation** | $0.560 \pm 0.233$ | — | Moderate rank concordance |
| **Sports with $\ge$ 1 Top-1** | **18 / 20** | 14 / 20 | More comprehensive organic coverage |
| **Most Concentrated Sport** | Archery (20.2%) | Shooting (31.7%) | TOPSIS heavily concentrates on low-demand sport |

### Granular Explainability Comparison
Demonstration for Student ID 1247 (Age 13):

* **Cluster-Based Output:** `"Cluster 3: high endurance affinity. Penalties: height 0.97, recovery 0.98"` *(Opaque, centroid-mediated)*.
* **ACS Output:** 
  * **Top-1:** Swimming (8.4/10) &mdash; `"Endurance 85th pctl (f=1.0), Upper Body 78th (f=0.7), Flexibility 73rd (f=1.0), Core 69th (f=0.7)"`
  * **Growth Target:** `"Upper body 78th → 85th pctl for max Swimming; Tier 2: Gymnastics"`
  * **Entry Sport:** `"Tier 3: Badminton (agility 52nd pctl)"`

---

## 📁 Project Structure & Mapping to Paper

```bash
sports-recommendation-engine/
├── src/
│   ├── expert_system/
│   │   ├── sport_profiles.py          # 20x6 Weight Matrix (Table 5) & Evidence Citations
│   │   ├── percentile_recommender.py  # ACS Core Engine: Percentile Norm & Function f
│   │   ├── three_tier_recommender.py  # Three-Tier Recommendation & LTAD Age Filtering
│   │   └── preprocessing.py           # Population percentile lookup generation
│   ├── clustering/
│   │   ├── model.py                   # K-Means baseline (k=6) & silhouette metrics
│   │   └── run.py                     # Cluster baseline execution script
│   └── data_pipeline/                 # Data loading and feature engineering (12 traits)
├── app/                               # Optional interactive REST API demonstration
├── data/                              # Data specifications and schema definitions
├── outputs/                           # Validation metrics and experiment logs
├── requirements.txt                   # Project dependencies
└── README.md                          # Repository documentation
```

---

## 🚀 Quick Start & Reproducibility

### Prerequisites
* Python 3.10 or higher
* `pip` package manager

### 1. Installation
```bash
git clone https://github.com/Khushijangra/sports-recommendation-engine.git
cd sports-recommendation-engine
pip install -r requirements.txt
```

### 2. Generate Recommendations using ACS
```python
from src.expert_system.three_tier_recommender import ThreeTierRecommender

# Initialize recommender with population percentiles
recommender = ThreeTierRecommender()

# Student fitness profile (raw percentiles 0–100 or test scores)
student = {
    'student_id': 1247,
    'age': 13,
    'CoreStrengthScore': 69.0,
    'UpperBodyStrengthScore': 78.0,
    'FlexibilityScore': 73.0,
    'EnduranceScore': 85.0,
    'SpeedScore': 58.0,
    'AgilityScore': 52.0
}

# Generate 3-tier recommendation
recommendations = recommender.recommend(student)

print("Tier 1 (Best Match):", [r['sport'] for r in recommendations['tier1_best_match']])
print("Tier 2 (Growth Potential):", [r['sport'] for r in recommendations['tier2_potential']])
print("Tier 3 (Entry Sports):", [r['sport'] for r in recommendations['tier3_entry']])
```

### 3. Run Validation Suite
To reproduce monotonicity, cross-fold stability, and weight perturbation checks:
```bash
python -m unittest discover -s src/expert_system
```

---

## ⚠️ Scope & Limitations

In accordance with our paper's explicit declarations (Section 7):
1. **Cross-Sectional Dataset:** This study was conducted on a cross-sectional dataset of 3,818 students. The internal validation tests confirm the structural robustness, mathematical monotonicity, and algorithmic stability of ACS.
2. **No Longitudinal Ground Truth:** The findings do not establish longitudinal real-world outcomes such as long-term athlete retention, medal performance, or injury rates.
3. **Weight Calibration:** While the stepped function $f$ absorbs tested $\pm$20% perturbations, the initial weights relocate rather than eliminate subjective expert decisions. Recalibration is advised when deploying in different national athletic frameworks.

---

## 📑 Citation

If you use this codebase or paper in your research, please cite:

```bibtex
@inproceedings{sheoran2026explainable,
  title     = {Explainable Youth Sports Recommendation Using Asymmetric Contribution Scoring},
  author    = { Jatin Sheoran , Khushi Jangra, Dr. Tapas Badal},
  booktitle = {Proceedings of the International Conference on Computer Science and Sports Analytics},
  series    = {Lecture Notes in Computer Science (LNCS)},
  publisher = {Springer},
  year      = {2026}
}
```

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
