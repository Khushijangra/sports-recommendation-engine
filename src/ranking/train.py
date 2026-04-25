"""
Train and evaluate a learning-to-rank model (XGBoost Ranker) using
the prepared long-form ranking dataset from outputs/data_prepared_rank.pkl.
Evaluates NDCG@k, MAP@k, and Hit@k, and exports ranked predictions.
"""

import os
import json
import numpy as np
import pandas as pd
import pickle
from typing import List, Dict, Tuple
from xgboost import XGBRanker
from src.ranking.metrics import groupwise_eval


def main():
    print("\n" + "="*80)
    print("XGB RANKER: TRAINING & EVALUATION")
    print("="*80)

    with open('outputs/data_prepared_rank.pkl', 'rb') as f:
        data = pickle.load(f)

    X_train = data['X_train']
    y_train = data['y_train']
    group_train = data['group_train']
    X_val = data['X_val']
    y_val = data['y_val']
    group_val = data['group_val']
    X_test = data['X_test']
    y_test = data['y_test']
    group_test = data['group_test']
    feature_names = data['X_columns']
    test_student_id = data.get('test_student_id', [])
    test_sport = data.get('test_sport', [])

    model = XGBRanker(
        objective='rank:ndcg',
        eval_metric='ndcg@10',
        learning_rate=0.08,
        max_depth=4,
        n_estimators=400,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_weight=6,
        reg_alpha=0.6,
        reg_lambda=2.0,
        random_state=42,
        n_jobs=-1,
        verbosity=0
    )

    model.fit(
        X_train, y_train,
        group=group_train,
        eval_set=[(X_val, y_val)],
        eval_group=[group_val],
        verbose=False
    )

    val_preds = model.predict(X_val)
    test_preds = model.predict(X_test)

    val_metrics = groupwise_eval(y_val, val_preds, group_val)
    test_metrics = groupwise_eval(y_test, test_preds, group_test)

    os.makedirs('outputs', exist_ok=True)
    ranking_metrics = {
        'validation': val_metrics,
        'test': test_metrics,
        'feature_count': len(feature_names),
        'params': {
            'objective': 'rank:ndcg',
            'eval_metric': 'ndcg@10',
            'learning_rate': 0.08,
            'max_depth': 4,
            'n_estimators': 400,
            'subsample': 0.85,
            'colsample_bytree': 0.85,
            'min_child_weight': 6,
            'reg_alpha': 0.6,
            'reg_lambda': 2.0,
        }
    }
    with open('outputs/ranking_metrics.json', 'w') as f:
        json.dump(ranking_metrics, f, indent=2)

    idx = 0
    rows = []
    cursor = 0
    for g in group_test:
        scores = test_preds[idx: idx + g]
        sid_slice = test_student_id[cursor: cursor + g] if test_student_id else [''] * g
        sport_slice = test_sport[cursor: cursor + g] if test_sport else [''] * g
        order = np.argsort(-scores)
        for rank_pos, local_i in enumerate(order[:min(10, g)], start=1):
            rows.append({
                'student_id': sid_slice[local_i],
                'sport': sport_slice[local_i],
                'rank_position': int(rank_pos),
                'predicted_score': float(scores[local_i]),
            })
        idx += g
        cursor += g
    pred_df = pd.DataFrame(rows)
    pred_df.to_csv('outputs/ranking_predictions_top10.csv', index=False)

    os.makedirs('models', exist_ok=True)
    with open('models/xgb_ranker.pkl', 'wb') as f:
        pickle.dump(model, f)

    print("\n[OK] Ranking model trained and evaluated")
    print("  - outputs/ranking_metrics.json")
    print("  - outputs/ranking_predictions_top10.csv")
    print("  - models/xgb_ranker.pkl")


if __name__ == "__main__":
    main()


