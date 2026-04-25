"""
Data Preprocessing Module for Sports Recommendation System
===========================================================
Handles data cleaning, age-normalization, and feature engineering.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Get paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / 'data'


def load_data(filepath=None):
    """Load and clean the student dataset."""
    if filepath is None:
        filepath = DATA_DIR / 'students.csv'
    
    df = pd.read_csv(filepath)
    
    # Simplify column names
    df.columns = [col.replace('computed_metrics.', '').replace('_', '') for col in df.columns]
    
    return df


def clean_data(df):
    """Clean data by handling anomalies and outliers."""
    df_clean = df.copy()
    
    # Fix Age anomalies (Age < 5 or missing)
    # Use class-based age estimation for anomalies
    class_to_age = {
        'Class 1': 6, 'Class 2': 7, 'Class 3': 8, 'Class 4': 9, 'Class 5': 10,
        'Class 6': 11, 'Class 7': 12, 'Class 8': 13, 'Class 9': 14, 'Class 10': 15,
        'Class 11': 16, 'Class 12': 17
    }
    
    for idx, row in df_clean.iterrows():
        if row['Age'] < 5 or pd.isna(row['Age']):
            estimated_age = class_to_age.get(row['classname'], 12)
            df_clean.at[idx, 'Age'] = estimated_age
    
    # Fix extreme BMI values (likely data entry errors)
    # BMI > 50 or < 10 are physiologically improbable
    median_bmi = df_clean[(df_clean['BMI'] >= 10) & (df_clean['BMI'] <= 50)]['BMI'].median()
    df_clean.loc[(df_clean['BMI'] < 10) | (df_clean['BMI'] > 50), 'BMI'] = median_bmi
    
    return df_clean


def compute_age_normalized_scores(df):
    """
    Compute age-normalized scores using percentile ranks within age groups.
    This allows fair comparison across different age groups.
    """
    df_norm = df.copy()
    
    performance_cols = [
        'CoreStrengthScore', 'UpperBodyStrengthScore', 'FlexibilityScore',
        'EnduranceScore', 'SpeedScore', 'AgilityScore'
    ]
    
    # Create age groups
    age_bins = [5, 8, 11, 14, 18]
    age_labels = ['6-8', '9-11', '12-14', '15-18']
    df_norm['AgeGroup'] = pd.cut(df_norm['Age'], bins=age_bins, labels=age_labels, include_lowest=True)
    
    # Compute percentile rank within each age group
    for col in performance_cols:
        norm_col = f'{col}_Norm'
        df_norm[norm_col] = df_norm.groupby('AgeGroup')[col].rank(pct=True) * 10
    
    return df_norm


def compute_composite_features(df):
    """Create composite features that combine related metrics."""
    df_comp = df.copy()
    
    # Power Index: Core + Upper Body Strength
    df_comp['PowerIndex'] = (df_comp['CoreStrengthScore'] + df_comp['UpperBodyStrengthScore']) / 2
    
    # Agility-Speed Index: Agility + Speed
    df_comp['AgilitySpeedIndex'] = (df_comp['AgilityScore'] + df_comp['SpeedScore']) / 2
    
    # Endurance-Flexibility Index
    df_comp['EnduranceFlexIndex'] = (df_comp['EnduranceScore'] + df_comp['FlexibilityScore']) / 2
    
    return df_comp


def preprocess_full(filepath=None):
    """Run the full preprocessing pipeline."""
    df = load_data(filepath)
    df = clean_data(df)
    df = compute_age_normalized_scores(df)
    df = compute_composite_features(df)
    return df


if __name__ == "__main__":
    print("Running preprocessing pipeline...")
    df = preprocess_full()
    print(f"Processed {len(df)} students")
    print(f"Columns: {df.columns.tolist()}")
    
    # Save processed data
    output_path = DATA_DIR / 'students_processed.csv'
    df.to_csv(output_path, index=False)
    print(f"Saved to {output_path}")
