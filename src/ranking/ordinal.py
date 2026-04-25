"""
Ordinal regression baseline on rank indices (0..9) using pointwise XGBRegressor.
Evaluates with the same groupwise metrics by sorting predictions within each student.
Outputs:
  - outputs/ordinal_rank_metrics.json
  - outputs/ordinal_rank_predictions_top10.csv
  - models/xgb_ordinal_rank.pkl
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from typing import List, Dict
from xgboost import XGBRegressor
from src.ranking.metrics import groupwise_eval


def main():
    with open('outputs/data_prepared_rank.pkl', 'rb') as f:
        data = pickle.load(f)

    X_train = data['X_train']
    y_train = data['y_train']
    X_val = data['X_val']
    y_val = data['y_val']
    X_test = data['X_test']
    y_test = data['y_test']
    group_val = data['group_val']
    group_test = data['group_test']
    test_student_id = data.get('test_student_id', [])
    test_sport = data.get('test_sport', [])

    model = XGBRegressor(
        n_estimators=500,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_alpha=0.3,
        reg_lambda=2.0,
        random_state=42,
        n_jobs=-1,
        verbosity=0
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    val_preds = model.predict(X_val)
    test_preds = model.predict(X_test)

    val_metrics = groupwise_eval(y_val, val_preds, group_val)
    test_metrics = groupwise_eval(y_test, test_preds, group_test)

    os.makedirs('outputs', exist_ok=True)
    os.makedirs('models', exist_ok=True)

    with open('outputs/ordinal_rank_metrics.json', 'w') as f:
        json.dump({'validation': val_metrics, 'test': test_metrics}, f, indent=2)

    rows = []
    idx = 0
    cursor = 0
    for g in group_test:
        scores = test_preds[idx: idx + g]
        sid_slice = test_student_id[cursor: cursor + g] if test_student_id else [''] * g
        sport_slice = test_sport[cursor: cursor + g] if test_sport else [''] * g
        order = np.argsort(-scores)[:min(10, g)]
        for rank_pos, local_i in enumerate(order, start=1):
            rows.append({
                'student_id': sid_slice[local_i],
                'sport': sport_slice[local_i],
                'rank_position': int(rank_pos),
                'predicted_score': float(scores[local_i]),
            })
        idx += g
        cursor += g
    pd.DataFrame(rows).to_csv('outputs/ordinal_rank_predictions_top10.csv', index=False)

    with open('models/xgb_ordinal_rank.pkl', 'wb') as f:
        pickle.dump(model, f)

    print("[OK] Ordinal rank baseline trained and exported.")


if __name__ == '__main__':
    main()


