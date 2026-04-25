"""
Hyperparameter tuning for XGBRanker using Optuna.
Optimizes NDCG@10 on validation groups, retrains with best params,
evaluates on test, and exports tuned metrics and predictions.
"""

import os
import json
import pickle
import optuna
import numpy as np
import pandas as pd
from typing import Dict
from xgboost import XGBRanker
from src.ranking.metrics import groupwise_eval


def objective(trial: optuna.trial.Trial, data: Dict) -> float:
    X_train = data['X_train']
    y_train = data['y_train']
    group_train = data['group_train']
    X_val = data['X_val']
    y_val = data['y_val']
    group_val = data['group_val']

    params = {
        'objective': 'rank:ndcg',
        'eval_metric': 'ndcg@10',
        'learning_rate': trial.suggest_float('learning_rate', 0.03, 0.2, log=True),
        'max_depth': trial.suggest_int('max_depth', 3, 7),
        'n_estimators': trial.suggest_int('n_estimators', 200, 600),
        'subsample': trial.suggest_float('subsample', 0.6, 0.95),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 0.95),
        'min_child_weight': trial.suggest_int('min_child_weight', 3, 12),
        'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 1.5),
        'reg_lambda': trial.suggest_float('reg_lambda', 0.5, 3.0),
        'random_state': 42,
        'n_jobs': -1,
        'verbosity': 0,
    }

    model = XGBRanker(**params)
    model.fit(
        X_train, y_train,
        group=group_train,
        eval_set=[(X_val, y_val)],
        eval_group=[group_val],
        verbose=False
    )
    preds = model.predict(X_val)
    metrics = groupwise_eval(y_val, preds, group_val)
    return metrics['ndcg@10']


def main():
    with open('outputs/data_prepared_rank.pkl', 'rb') as f:
        data = pickle.load(f)

    study = optuna.create_study(direction='maximize', study_name='xgb_ranker_opt')
    study.optimize(lambda tr: objective(tr, data), n_trials=25, show_progress_bar=False)

    best_params = study.best_trial.params
    best_value = study.best_value

    tuned_params = {
        'objective': 'rank:ndcg',
        'eval_metric': 'ndcg@10',
        'random_state': 42,
        'n_jobs': -1,
        'verbosity': 0,
        **best_params
    }

    model = XGBRanker(**tuned_params)
    model.fit(
        data['X_train'], data['y_train'],
        group=data['group_train'],
        eval_set=[(data['X_val'], data['y_val'])],
        eval_group=[data['group_val']],
        verbose=False
    )

    val_preds = model.predict(data['X_val'])
    test_preds = model.predict(data['X_test'])

    val_metrics = groupwise_eval(data['y_val'], val_preds, data['group_val'])
    test_metrics = groupwise_eval(data['y_test'], test_preds, data['group_test'])

    os.makedirs('outputs', exist_ok=True)
    os.makedirs('models', exist_ok=True)

    with open('outputs/ranking_optimization_results.json', 'w') as f:
        json.dump({'best_params': best_params, 'best_ndcg10': float(best_value)}, f, indent=2)

    with open('outputs/ranking_metrics_tuned.json', 'w') as f:
        json.dump({'validation': val_metrics, 'test': test_metrics, 'best_params': tuned_params}, f, indent=2)

    test_student_id = data.get('test_student_id', [])
    test_sport = data.get('test_sport', [])
    rows = []
    idx = 0
    cursor = 0
    for g in data['group_test']:
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
    pd.DataFrame(rows).to_csv('outputs/ranking_predictions_top10_tuned.csv', index=False)

    with open('models/xgb_ranker_tuned.pkl', 'wb') as f:
        pickle.dump(model, f)


if __name__ == "__main__":
    main()


