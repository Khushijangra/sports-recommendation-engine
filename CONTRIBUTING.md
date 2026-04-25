# Contributing to SportMatch

## Getting Started

```bash
git clone https://github.com/YOUR_USERNAME/SportMatch.git
cd SportMatch
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate    # Linux/Mac
pip install -r requirements.txt
```

## Contribution Areas

| Area | Notes |
|------|-------|
| 🤖 ML Pipeline | New baselines, feature engineering, evaluation metrics |
| 🧠 Expert System | New sports, refined weight profiles, improved tier logic |
| 🌐 Web App | UI improvements, new API endpoints, performance |
| 📊 Evaluation | New metrics, improved visualizations |
| 📚 Documentation | Clarifications, examples, architecture diagrams |
| ⚡ Performance | Inference speed, memory optimization |

## Adding a New Sport

1. Add a profile to `src/expert_system/sport_profiles.py`:
   - Define 6 attribute weights (0.0–1.0)
   - Include `sport_type`, `height_preference`, `description`
   - Add at least 2 supporting references in the `evidence` list
2. Update `SPORTS_LIST` and `SPORT_CATEGORIES`
3. Add age restriction logic in `three_tier_recommender.py` if needed
4. Rebuild the training dataset (`src/ranking/prepare.py`) to include the new sport
5. Retrain the model to reflect the expanded catalog

## Code Style

- PEP 8 for Python
- Docstrings on all public functions and classes
- Type hints preferred for function signatures
- Functions under ~50 lines; extract helpers as needed

## Pull Request Process

1. Fork → feature branch (`git checkout -b feature/new-sport`)
2. Make changes + update documentation
3. Verify `.gitignore` is respected before staging (`python scripts/check_before_push.py`)
4. Submit PR with a clear description of the change and rationale

## Data Privacy

**Never commit real student data.** The full dataset is excluded by `.gitignore`.
Only `data/sample_students.csv` (100 anonymized rows) is public.

Before any `git add`, run:
```bash
python scripts/check_before_push.py
```

## Code of Conduct

Be constructive and respectful. We follow the [Contributor Covenant](https://www.contributor-covenant.org/).
