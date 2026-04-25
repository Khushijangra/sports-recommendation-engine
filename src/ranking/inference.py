"""
Ranking inference utility.
Loads the tuned production ranker (fallback to baseline), and predicts top-K sports
for each input row. Input CSV must contain the same non-sport features as training
(`outputs/data_prepared_rank.pkl` -> `X_columns` minus `sport_` one-hots).
Usage:
  python src/ranking/inference.py --input features.csv --output outputs/ranking_inference_top10.csv --k 10
"""

import argparse
import pickle
import os
import numpy as np
import pandas as pd


def load_ranker():
    tuned = 'models/xgb_ranker_tuned.pkl'
    prod = 'models/xgb_ranker_production.pkl'
    base = 'models/xgb_ranker.pkl'
    if os.path.exists(prod):
        with open(prod, 'rb') as f:
            return pickle.load(f), 'production'
    if os.path.exists(tuned):
        with open(tuned, 'rb') as f:
            return pickle.load(f), 'tuned'
    with open(base, 'rb') as f:
        return pickle.load(f), 'baseline'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Path to CSV with features per student row')
    parser.add_argument('--output', default='outputs/ranking_inference_top10.csv', help='Output CSV path')
    parser.add_argument('--k', type=int, default=10, help='Top-K to return')
    args = parser.parse_args()

    os.makedirs('outputs', exist_ok=True)

    with open('outputs/data_prepared_rank.pkl', 'rb') as f:
        meta = pickle.load(f)
    X_columns = meta['X_columns']
    catalog = meta['catalog_sports']

    sport_ohe_cols = [c for c in X_columns if c.startswith('sport_')]
    base_cols = [c for c in X_columns if c not in sport_ohe_cols]
    base_cols = [c for c in base_cols if c not in ('student_id', 'rank_idx', 'relevance', 'score')]

    df_in = pd.read_csv(args.input)
    for col in base_cols:
        if col not in df_in.columns:
            df_in[col] = 0.0
    X_base = df_in[base_cols].copy()

    model, which = load_ranker()

    rows = []
    for idx in range(len(X_base)):
        x_row = X_base.iloc[idx:idx+1].to_numpy()
        X_rep = np.repeat(x_row, len(catalog), axis=0)
        sport_matrix = np.zeros((len(catalog), len(sport_ohe_cols)), dtype=float)
        col_index = {c: j for j, c in enumerate(sport_ohe_cols)}
        for i, sport in enumerate(catalog):
            col_name = f'sport_{sport}'
            j = col_index.get(col_name, None)
            if j is not None:
                sport_matrix[i, j] = 1.0
        X_full = np.zeros((len(catalog), len(X_columns)), dtype=float)
        base_index = {c: j for j, c in enumerate(base_cols)}
        for j, col in enumerate(X_columns):
            if col in base_index:
                X_full[:, j] = X_rep[:, base_index[col]]
            elif col in col_index:
                X_full[:, j] = sport_matrix[:, col_index[col]]
            else:
                X_full[:, j] = 0.0
        scores = model.predict(X_full)
        order = np.argsort(-scores)[:args.k]
        for rank_pos, i in enumerate(order, start=1):
            rows.append({
                'row_index': idx,
                'sport': catalog[i],
                'rank_position': rank_pos,
                'predicted_score': float(scores[i]),
            })

    pd.DataFrame(rows).to_csv(args.output, index=False)
    print(f"[OK] Inference complete using {which} ranker → {args.output}")


if __name__ == '__main__':
    main()


