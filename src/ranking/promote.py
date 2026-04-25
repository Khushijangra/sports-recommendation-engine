"""
Promote tuned ranker to production.
Copies models/xgb_ranker_tuned.pkl -> models/xgb_ranker_production.pkl
and writes outputs/ranker_production_metadata.json.
"""

import os
import json
import shutil
from datetime import datetime


def main():
    tuned = 'models/xgb_ranker_tuned.pkl'
    prod = 'models/xgb_ranker_production.pkl'
    os.makedirs('models', exist_ok=True)
    os.makedirs('outputs', exist_ok=True)
    if not os.path.exists(tuned):
        raise FileNotFoundError("Tuned model not found: models/xgb_ranker_tuned.pkl")
    shutil.copyfile(tuned, prod)
    meta = {
        'source': tuned,
        'destination': prod,
        'promoted_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'notes': 'Tuned ranker promoted to production.'
    }
    with open('outputs/ranker_production_metadata.json', 'w') as f:
        json.dump(meta, f, indent=2)
    print("[OK] Promoted tuned ranker to production.")


if __name__ == '__main__':
    main()


