"""
Ranking Dataset Preparation
Build a student–sport long-form dataset with rank indices (0..9) from data/Sports_Data.csv,
derive features using the existing rebuild pipeline (phases 1–6), and save grouped splits
ready for learning-to-rank models (e.g., XGBRanker).
"""

import os
import json
from typing import List, Dict, Any

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

from src.data_pipeline.rebuild_dataset import (
    phase1_load_inspection,
    phase2_structural_cleanup,
    phase3_validation_correction,
    phase4_encoding_standardization,
    phase5_normalization,
    phase6_feature_engineering,
)


def build_long_form_from_recommendations(df_with_sports: pd.DataFrame) -> pd.DataFrame:
    required_id = 'student_id'
    if required_id not in df_with_sports.columns:
        raise ValueError("student_id not found in dataset derived from Sports_Data.csv")

    sport_cols = []
    score_cols = {}
    for i in range(10):
        sport_col = f'sport_recommendations[{i}].sport'
        score_col = f'sport_recommendations[{i}].score'
        if sport_col in df_with_sports.columns:
            sport_cols.append((i, sport_col))
        if score_col in df_with_sports.columns:
            score_cols[i] = score_col

    if len(sport_cols) == 0:
        raise ValueError("No sport_recommendations[i].sport columns found (0..9).")

    long_rows = []
    base = df_with_sports[[required_id]].copy()
    base = base.drop_duplicates(subset=[required_id])

    for i, sport_col in sport_cols:
        score_col = score_cols.get(i, None)
        df_slice = df_with_sports[[required_id, sport_col]].copy()
        df_slice = df_slice.rename(columns={sport_col: 'sport'})
        if score_col and score_col in df_with_sports.columns:
            df_slice['score'] = df_with_sports[score_col]
        else:
            df_slice['score'] = np.nan
        df_slice['rank_idx'] = i
        df_slice['relevance'] = 10 - i  # higher is better
        df_slice = df_slice[df_slice['sport'].astype(str).str.len() > 0]
        long_rows.append(df_slice)

    long_df = pd.concat(long_rows, axis=0, ignore_index=True)
    long_df = long_df.drop_duplicates(subset=['student_id', 'sport', 'rank_idx'])
    return long_df


def prepare_features_from_pipeline() -> pd.DataFrame:
    df_raw, non_predictive_cols, _ = phase1_load_inspection()
    df = phase2_structural_cleanup(df_raw, non_predictive_cols)
    df = phase3_validation_correction(df)
    df = phase4_encoding_standardization(df)
    df = phase5_normalization(df)
    df = phase6_feature_engineering(df)
    return df


def one_hot_encode_sport(df_long: pd.DataFrame) -> pd.DataFrame:
    if 'sport' not in df_long.columns:
        raise ValueError("'sport' column is missing in long-form dataset.")
    sport_dummies = pd.get_dummies(df_long['sport'], prefix='sport')
    return pd.concat([df_long.drop(columns=['sport']), sport_dummies], axis=1)


def build_group_array(df_split: pd.DataFrame, group_key: str) -> List[int]:
    return df_split.groupby(group_key).size().tolist()


def main():
    print("\n" + "="*80)
    print("RANKING DATASET PREPARATION")
    print("="*80)

    df_raw, _, _ = phase1_load_inspection()

    features_df = prepare_features_from_pipeline()

    long_df = build_long_form_from_recommendations(df_raw)

    rec_cols = [c for c in features_df.columns if c.startswith('sport_recommendations[')]
    feat_cols = [c for c in features_df.columns if c not in rec_cols]
    features_clean = features_df[feat_cols].copy()

    merged = long_df.merge(features_clean, on='student_id', how='left', validate='many_to_one')

    merged_ohe = one_hot_encode_sport(merged)

    target_col = 'relevance'
    group_key = 'student_id'

    non_numeric_cols = merged_ohe.select_dtypes(include=['object']).columns
    cols_to_drop_non_numeric = [c for c in non_numeric_cols if c not in {group_key}]
    if cols_to_drop_non_numeric:
        merged_ohe = merged_ohe.drop(columns=cols_to_drop_non_numeric)

    exclude_cols = {'rank_idx', 'relevance', 'score'}
    id_cols = {'student_id'}
    X_cols = [c for c in merged_ohe.columns if c not in exclude_cols.union(id_cols)]

    students = merged_ohe[group_key].drop_duplicates().values
    students_train, students_temp = train_test_split(students, test_size=0.30, random_state=42)
    students_val, students_test = train_test_split(students_temp, test_size=0.50, random_state=42)

    train_df = merged_ohe[merged_ohe[group_key].isin(students_train)]
    val_df = merged_ohe[merged_ohe[group_key].isin(students_val)]
    test_df = merged_ohe[merged_ohe[group_key].isin(students_test)]

    merged_meta = merged[[group_key, 'sport', 'rank_idx']].copy()
    train_meta = merged_meta[merged_meta[group_key].isin(students_train)]
    val_meta = merged_meta[merged_meta[group_key].isin(students_val)]
    test_meta = merged_meta[merged_meta[group_key].isin(students_test)]

    train_df = train_df.sort_values([group_key, 'rank_idx']).reset_index(drop=True)
    val_df = val_df.sort_values([group_key, 'rank_idx']).reset_index(drop=True)
    test_df = test_df.sort_values([group_key, 'rank_idx']).reset_index(drop=True)
    train_meta = train_meta.sort_values([group_key, 'rank_idx']).reset_index(drop=True)
    val_meta = val_meta.sort_values([group_key, 'rank_idx']).reset_index(drop=True)
    test_meta = test_meta.sort_values([group_key, 'rank_idx']).reset_index(drop=True)

    group_train = build_group_array(train_df, group_key)
    group_val = build_group_array(val_df, group_key)
    group_test = build_group_array(test_df, group_key)

    X_train = train_df[X_cols].values
    y_train = train_df[target_col].values
    X_val = val_df[X_cols].values
    y_val = val_df[target_col].values
    X_test = test_df[X_cols].values
    y_test = test_df[target_col].values

    os.makedirs('outputs', exist_ok=True)
    os.makedirs('models', exist_ok=True)

    data_prepared_rank = {
        'X_train': X_train,
        'y_train': y_train,
        'group_train': group_train,
        'X_val': X_val,
        'y_val': y_val,
        'group_val': group_val,
        'X_test': X_test,
        'y_test': y_test,
        'group_test': group_test,
        'X_columns': X_cols,
        'group_key': group_key,
        'students_train': list(map(str, students_train)),
        'students_val': list(map(str, students_val)),
        'students_test': list(map(str, students_test)),
        'val_student_id': val_meta[group_key].astype(str).tolist(),
        'val_sport': val_meta['sport'].astype(str).tolist(),
        'test_student_id': test_meta[group_key].astype(str).tolist(),
        'test_sport': test_meta['sport'].astype(str).tolist(),
        'catalog_sports': sorted({c.replace('sport_', '') for c in X_cols if c.startswith('sport_')}),
        'long_df_shape': tuple(merged_ohe.shape),
    }

    import pickle
    with open('outputs/data_prepared_rank.pkl', 'wb') as f:
        pickle.dump(data_prepared_rank, f)

    summary = {
        'X_train_shape': list(X_train.shape),
        'X_val_shape': list(X_val.shape),
        'X_test_shape': list(X_test.shape),
        'n_features': len(X_cols),
        'group_train_len': len(group_train),
        'group_val_len': len(group_val),
        'group_test_len': len(group_test),
        'catalog_size': len(data_prepared_rank['catalog_sports']),
        'long_df_shape': data_prepared_rank['long_df_shape'],
    }
    with open('outputs/ranking_data_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print("\n[OK] Ranking dataset prepared")
    print(f"  - outputs/data_prepared_rank.pkl")
    print(f"  - outputs/ranking_data_summary.json")


if __name__ == "__main__":
    main()


