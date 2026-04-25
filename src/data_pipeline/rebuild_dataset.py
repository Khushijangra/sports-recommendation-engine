"""
Final Model Dataset Rebuild Script
Rebuilds the entire model dataset from data/Sports_Data.csv through 9 sequential phases.
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder
from datetime import datetime
import os
import warnings
warnings.filterwarnings('ignore')

# Initialize report log
report_log = []

def log_phase(phase_num, phase_name, details):
    """Log phase completion details"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_log.append(f"\n## Phase {phase_num}: {phase_name}\n")
    report_log.append(f"Completed at: {timestamp}\n")
    for detail in details:
        report_log.append(f"- {detail}\n")
    print(f"[OK] Phase {phase_num}: {phase_name} completed")

# ============================================================================
# PHASE 1: Load & Initial Inspection
# ============================================================================

def phase1_load_inspection():
    """Phase 1: Load CSV and perform initial inspection"""
    print("\n" + "="*80)
    print("PHASE 1: Load & Initial Inspection")
    print("="*80)
    
    df_raw = pd.read_csv('data/Sports_Data.csv')
    
    # Record initial statistics
    initial_shape = df_raw.shape
    memory_usage = df_raw.memory_usage(deep=True).sum() / 1024**2  # MB
    column_names = list(df_raw.columns)
    dtypes_summary = df_raw.dtypes.value_counts().to_dict()
    null_counts = df_raw.isnull().sum()
    null_counts_nonzero = null_counts[null_counts > 0]
    
    # Detect non-predictive columns
    non_predictive_patterns = [
        "_id", "student_name", "student_student_id", "pet_id",
        "ai_narrative", "ai_narrative_generated", "ai_narrative_generated_at",
        "created_at", "updated_at", "assessment_type"
    ]
    
    non_predictive_cols = []
    for col in column_names:
        for pattern in non_predictive_patterns:
            if pattern in col:
                non_predictive_cols.append(col)
                break
    
    non_predictive_cols = list(set(non_predictive_cols))
    
    details = [
        f"Initial shape: {initial_shape[0]} rows × {initial_shape[1]} columns",
        f"Memory usage: {memory_usage:.2f} MB",
        f"Total columns: {len(column_names)}",
        f"Data types: {dtypes_summary}",
        f"Columns with nulls: {len(null_counts_nonzero)}",
        f"Non-predictive columns detected: {len(non_predictive_cols)}"
    ]
    
    if len(null_counts_nonzero) > 0:
        details.append(f"Null counts: {dict(null_counts_nonzero)}")
    
    log_phase(1, "Load & Initial Inspection", details)
    
    return df_raw, non_predictive_cols, initial_shape

# ============================================================================
# PHASE 2: Structural Cleanup
# ============================================================================

def phase2_structural_cleanup(df_raw, non_predictive_cols):
    """Phase 2: Drop non-predictive columns and keep core groups"""
    print("\n" + "="*80)
    print("PHASE 2: Structural Cleanup")
    print("="*80)
    
    df = df_raw.copy()
    
    # Drop non-predictive columns
    cols_to_drop = [col for col in non_predictive_cols if col in df.columns]
    df = df.drop(columns=cols_to_drop)
    
    # Define core groups to keep
    core_groups = {
        'identifiers': ['student_id'],
        'demographics': ['school_code', 'class_name', 'computed_metrics.Age', 'computed_metrics.Gender'],
        'physical': ['computed_metrics.Height_cm', 'computed_metrics.Weight_kg', 'computed_metrics.BMI'],
        'performance': [
            'computed_metrics.CoreStrengthScore', 'computed_metrics.UpperBodyStrengthScore',
            'computed_metrics.FlexibilityScore', 'computed_metrics.EnduranceScore',
            'computed_metrics.SpeedScore', 'computed_metrics.StrengthScore',
            'computed_metrics.AgilityScore', 'computed_metrics.OverallScore'
        ],
        'responses': [f'responses.{i}' for i in range(1, 8)],
        'label': ['sport_recommendations[0].sport']
    }
    
    # Collect all columns to keep
    cols_to_keep = []
    for group, cols in core_groups.items():
        for col in cols:
            if col in df.columns:
                cols_to_keep.append(col)
    
    # Also keep updated_at if it exists (for duplicate handling)
    if 'updated_at' in df.columns:
        cols_to_keep.append('updated_at')
    
    # Keep only core columns
    df = df[cols_to_keep]
    
    # Ensure student_id is preserved (required by plan)
    if 'student_id' not in df.columns and 'student_id' in df_raw.columns:
        df['student_id'] = df_raw['student_id'].iloc[:len(df)]
    
    # Handle duplicates by student_id (keep latest by updated_at if available)
    if 'student_id' in df.columns:
        if 'updated_at' in df.columns:
            df['updated_at'] = pd.to_datetime(df['updated_at'], errors='coerce')
            df = df.sort_values('updated_at', ascending=False)
            df = df.drop_duplicates(subset=['student_id'], keep='first')
            df = df.drop(columns=['updated_at'])
        else:
            df = df.drop_duplicates(subset=['student_id'], keep='first')
    
    details = [
        f"Dropped {len(cols_to_drop)} non-predictive columns",
        f"Kept {len(cols_to_keep)} core columns",
        f"Final shape after cleanup: {df.shape[0]} rows × {df.shape[1]} columns",
        f"Duplicates removed: {df_raw.shape[0] - df.shape[0]}"
    ]
    
    log_phase(2, "Structural Cleanup", details)
    
    return df

# ============================================================================
# PHASE 3: Data Validation & Correction
# ============================================================================

def phase3_validation_correction(df):
    """Phase 3: Validate and correct data"""
    print("\n" + "="*80)
    print("PHASE 3: Data Validation & Correction")
    print("="*80)
    
    df = df.copy()
    
    # Recalculate BMI
    if 'computed_metrics.Height_cm' in df.columns and 'computed_metrics.Weight_kg' in df.columns:
        height = df['computed_metrics.Height_cm']
        weight = df['computed_metrics.Weight_kg']
        df['computed_metrics.BMI'] = weight / ((height / 100) ** 2)
    
    # Enforce valid ranges
    range_limits = {
        'computed_metrics.Height_cm': [100, 220],
        'computed_metrics.Weight_kg': [20, 120],
        'computed_metrics.Age': [5, 25],
        'computed_metrics.BMI': [10, 40]
    }
    
    clipped_counts = {}
    for col, (min_val, max_val) in range_limits.items():
        if col in df.columns:
            before = df[col].copy()
            df[col] = df[col].clip(lower=min_val, upper=max_val)
            clipped = (before != df[col]).sum()
            if clipped > 0:
                clipped_counts[col] = clipped
    
    # Replace outliers outside 1st-99th percentile with boundary values
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    outlier_counts = {}
    for col in numeric_cols:
        if col in df.columns:
            q1 = df[col].quantile(0.01)
            q99 = df[col].quantile(0.99)
            before = df[col].copy()
            df[col] = df[col].clip(lower=q1, upper=q99)
            outliers = (before != df[col]).sum()
            if outliers > 0:
                outlier_counts[col] = outliers
    
    # Normalize Gender
    if 'computed_metrics.Gender' in df.columns:
        gender_mapping = {
            'Male': 'Male', 'male': 'Male', 'M': 'Male', 'm': 'Male',
            'Female': 'Female', 'female': 'Female', 'F': 'Female', 'f': 'Female'
        }
        df['computed_metrics.Gender'] = df['computed_metrics.Gender'].map(gender_mapping)
        df['computed_metrics.Gender'] = df['computed_metrics.Gender'].fillna('Male')  # Default
        
        # Encode Gender
        df['Gender_encoded'] = (df['computed_metrics.Gender'] == 'Male').astype(int)
    
    # Handle missing numeric values with median imputation by class_name or school_code
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    imputed_counts = {}
    for col in numeric_cols:
        if df[col].isnull().sum() > 0:
            if 'class_name' in df.columns:
                df[col] = df.groupby('class_name')[col].transform(lambda x: x.fillna(x.median()))
            elif 'school_code' in df.columns:
                df[col] = df.groupby('school_code')[col].transform(lambda x: x.fillna(x.median()))
            
            # If still missing, use global median
            if df[col].isnull().sum() > 0:
                df[col] = df[col].fillna(df[col].median())
                imputed_counts[col] = df[col].isnull().sum()
    
    # Validate: no missing, no inf
    missing_count = df.select_dtypes(include=[np.number]).isnull().sum().sum()
    inf_count = np.isinf(df.select_dtypes(include=[np.number])).sum().sum()
    
    details = [
        f"BMI recalculated from Height and Weight",
        f"Values clipped to valid ranges: {clipped_counts}",
        f"Outliers replaced (1st-99th percentile): {len(outlier_counts)} columns affected",
        f"Gender normalized to Male/Female and encoded",
        f"Missing values imputed: {len(imputed_counts)} columns",
        f"Final validation: Missing={missing_count}, Inf={inf_count}"
    ]
    
    if missing_count > 0 or inf_count > 0:
        raise ValueError(f"Validation failed: {missing_count} missing, {inf_count} inf values")
    
    log_phase(3, "Data Validation & Correction", details)
    
    return df

# ============================================================================
# PHASE 4: Encoding & Data Type Standardization
# ============================================================================

def phase4_encoding_standardization(df):
    """Phase 4: Encode categoricals and standardize data types"""
    print("\n" + "="*80)
    print("PHASE 4: Encoding & Data Type Standardization")
    print("="*80)
    
    df = df.copy()
    
    # Encode class_name to int8
    if 'class_name' in df.columns:
        le_class = LabelEncoder()
        df['class_name_encoded'] = le_class.fit_transform(df['class_name'].astype(str))
        df = df.drop(columns=['class_name'])
        df = df.rename(columns={'class_name_encoded': 'class_name'})
        df['class_name'] = df['class_name'].astype('int8')
    
    # One-hot encode school_code
    if 'school_code' in df.columns:
        school_dummies = pd.get_dummies(df['school_code'], prefix='school')
        df = pd.concat([df, school_dummies], axis=1)
        df = df.drop(columns=['school_code'])
    
    # Ensure Gender_encoded is int8
    if 'Gender_encoded' in df.columns:
        df['Gender_encoded'] = df['Gender_encoded'].astype('int8')
    
    # Convert all floats to float32
    float_cols = df.select_dtypes(include=['float64', 'float']).columns
    for col in float_cols:
        df[col] = df[col].astype('float32')
    
    # Drop boolean True/False columns, ensure binary 0/1
    bool_cols = df.select_dtypes(include=['bool']).columns
    for col in bool_cols:
        df[col] = df[col].astype('int8')
    
    # Check dtypes
    dtypes_summary = df.dtypes.value_counts().to_dict()
    
    details = [
        f"class_name encoded to int8",
        f"school_code one-hot encoded: {len([c for c in df.columns if c.startswith('school_')])} columns",
        f"Gender_encoded set to int8",
        f"All floats converted to float32: {len(float_cols)} columns",
        f"Boolean columns converted to int8: {len(bool_cols)} columns",
        f"Final dtype summary: {dtypes_summary}"
    ]
    
    log_phase(4, "Encoding & Data Type Standardization", details)
    
    return df

# ============================================================================
# PHASE 5: Per-Column Normalization
# ============================================================================

def phase5_normalization(df):
    """Phase 5: Apply per-column normalization"""
    print("\n" + "="*80)
    print("PHASE 5: Per-Column Normalization")
    print("="*80)
    
    df = df.copy()
    
    # Physical Metrics: Z-score
    physical_cols = [
        'computed_metrics.Height_cm', 'computed_metrics.Weight_kg',
        'computed_metrics.BMI', 'computed_metrics.Age'
    ]
    
    scaler_z = StandardScaler()
    for col in physical_cols:
        if col in df.columns:
            df[col + '_scaled'] = scaler_z.fit_transform(df[[col]])
            df = df.drop(columns=[col])
            df = df.rename(columns={col + '_scaled': col})
    
    # Responses 1-5: Min-Max [0,1]
    response_cols_1_5 = [f'responses.{i}' for i in range(1, 6)]
    scaler_mm = MinMaxScaler()
    for col in response_cols_1_5:
        if col in df.columns:
            df[col + '_scaled'] = scaler_mm.fit_transform(df[[col]])
            df = df.drop(columns=[col])
            df = df.rename(columns={col + '_scaled': col})
    
    # Responses 6 & 7: Invert first (1/x), then Min-Max
    response_cols_6_7 = ['responses.6', 'responses.7']
    for col in response_cols_6_7:
        if col in df.columns:
            # Invert (handle zeros)
            df[col + '_inverted'] = 1 / (df[col] + 1e-10)  # Add small epsilon to avoid division by zero
            # Min-Max scale
            scaler_mm = MinMaxScaler()
            df[col + '_scaled'] = scaler_mm.fit_transform(df[[col + '_inverted']])
            df = df.drop(columns=[col, col + '_inverted'])
            df = df.rename(columns={col + '_scaled': col})
    
    # Performance Metrics: Keep 0-10 scale (no scaling)
    # They remain as-is
    
    details = [
        f"Physical metrics (Height, Weight, BMI, Age): Z-score normalized",
        f"Responses 1-5: Min-Max scaled to [0,1]",
        f"Responses 6-7: Inverted then Min-Max scaled to [0,1]",
        f"Performance metrics: Kept on 0-10 scale (no scaling)"
    ]
    
    log_phase(5, "Per-Column Normalization", details)
    
    return df

# ============================================================================
# PHASE 6: Feature Engineering
# ============================================================================

def phase6_feature_engineering(df):
    """Phase 6: Compute domain-relevant features"""
    print("\n" + "="*80)
    print("PHASE 6: Feature Engineering")
    print("="*80)
    
    df = df.copy()
    
    # Get column names (may have been renamed)
    height_col = 'computed_metrics.Height_cm'
    weight_col = 'computed_metrics.Weight_kg'
    bmi_col = 'computed_metrics.BMI'
    
    # Performance score columns
    core_col = 'computed_metrics.CoreStrengthScore'
    strength_col = 'computed_metrics.StrengthScore'
    upper_col = 'computed_metrics.UpperBodyStrengthScore'
    flexibility_col = 'computed_metrics.FlexibilityScore'
    endurance_col = 'computed_metrics.EnduranceScore'
    speed_col = 'computed_metrics.SpeedScore'
    agility_col = 'computed_metrics.AgilityScore'
    
    # 1. height_weight_ratio
    if height_col in df.columns and weight_col in df.columns:
        df['height_weight_ratio'] = (df[height_col] / (df[weight_col] + 1e-10)).round(5)
    
    # 2. strength_to_weight_ratio
    if strength_col in df.columns and weight_col in df.columns:
        df['strength_to_weight_ratio'] = (df[strength_col] / (df[weight_col] + 1e-10)).round(5)
    
    # 3. endurance_per_bmi
    if endurance_col in df.columns and bmi_col in df.columns:
        df['endurance_per_bmi'] = (df[endurance_col] / (df[bmi_col] + 1e-10)).round(5)
    
    # 4. flexibility_strength_ratio
    if flexibility_col in df.columns and strength_col in df.columns:
        df['flexibility_strength_ratio'] = (df[flexibility_col] / (df[strength_col] + 1e-10)).round(5)
    
    # 5. speed_agility_ratio
    if speed_col in df.columns and agility_col in df.columns:
        df['speed_agility_ratio'] = (df[speed_col] / (df[agility_col] + 1e-10)).round(5)
    
    # 6. power_index = mean(CoreStrength, Strength, UpperBodyStrength)
    power_cols = [c for c in [core_col, strength_col, upper_col] if c in df.columns]
    if len(power_cols) > 0:
        df['power_index'] = df[power_cols].mean(axis=1).round(5)
    
    # 7. endurance_index = mean(Endurance, Speed, Agility)
    endurance_cols = [c for c in [endurance_col, speed_col, agility_col] if c in df.columns]
    if len(endurance_cols) > 0:
        df['endurance_index'] = df[endurance_cols].mean(axis=1).round(5)
    
    # 8. balance_index = std of all 7 performance metrics
    perf_cols = [c for c in [core_col, upper_col, flexibility_col, endurance_col, 
                             speed_col, strength_col, agility_col] if c in df.columns]
    if len(perf_cols) > 0:
        df['balance_index'] = df[perf_cols].std(axis=1).round(5)
    
    # 9. overall_fitness_index = mean of 7 performance metrics
    if len(perf_cols) > 0:
        df['overall_fitness_index'] = df[perf_cols].mean(axis=1).round(5)
    
    # Remove columns with 0 variance
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    zero_var_cols = []
    for col in numeric_cols:
        if df[col].var() == 0:
            zero_var_cols.append(col)
    
    if zero_var_cols:
        df = df.drop(columns=zero_var_cols)
    
    engineered_features = [
        'height_weight_ratio', 'strength_to_weight_ratio', 'endurance_per_bmi',
        'flexibility_strength_ratio', 'speed_agility_ratio', 'power_index',
        'endurance_index', 'balance_index', 'overall_fitness_index'
    ]
    
    features_added = [f for f in engineered_features if f in df.columns]
    
    details = [
        f"Engineered features added: {len(features_added)}",
        f"Features: {', '.join(features_added)}",
        f"Zero-variance columns removed: {len(zero_var_cols)}"
    ]
    
    log_phase(6, "Feature Engineering", details)
    
    return df

# ============================================================================
# PHASE 7: Label Reintegration
# ============================================================================

def phase7_label_reintegration(df):
    """Phase 7: Extract and encode sport label"""
    print("\n" + "="*80)
    print("PHASE 7: Label Reintegration")
    print("="*80)
    
    df = df.copy()
    
    # Extract sport_recommendations[0].sport
    label_col = 'sport_recommendations[0].sport'
    if label_col not in df.columns:
        raise ValueError(f"Label column {label_col} not found")
    
    # Rename to sport_label
    df['sport_label'] = df[label_col]
    df = df.drop(columns=[label_col])
    
    # Drop all other sport_recommendations columns
    sport_cols = [c for c in df.columns if 'sport_recommendations' in c]
    df = df.drop(columns=sport_cols)
    
    # Verify no null labels
    null_labels = df['sport_label'].isnull().sum()
    if null_labels > 0:
        raise ValueError(f"Found {null_labels} null labels")
    
    # Encode labels numerically
    le_sport = LabelEncoder()
    df['sport_label_encoded'] = le_sport.fit_transform(df['sport_label'].astype(str))
    sport_label_mapping = dict(zip(le_sport.classes_, range(len(le_sport.classes_))))
    
    # Get label distribution
    label_counts = df['sport_label'].value_counts().to_dict()
    
    details = [
        f"Label column extracted: sport_recommendations[0].sport → sport_label",
        f"Other sport_recommendations columns dropped: {len(sport_cols) - 1}",
        f"Null labels: {null_labels}",
        f"Unique labels: {len(label_counts)}",
        f"Label distribution: {dict(list(label_counts.items())[:10])}"  # Show first 10
    ]
    
    log_phase(7, "Label Reintegration", details)
    
    return df, sport_label_mapping, label_counts

# ============================================================================
# PHASE 8: Quality and Leakage Audit
# ============================================================================

def phase8_quality_audit(df, initial_shape):
    """Phase 8: Perform comprehensive quality and leakage audit"""
    print("\n" + "="*80)
    print("PHASE 8: Quality and Leakage Audit")
    print("="*80)
    
    df = df.copy()
    
    audit_results = []
    
    # Check: 0 missing, 0 inf, all numeric
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    missing_count = df[numeric_cols].isnull().sum().sum()
    inf_count = np.isinf(df[numeric_cols]).sum().sum()
    audit_results.append(f"Missing values: {missing_count}")
    audit_results.append(f"Infinite values: {inf_count}")
    
    # Row count consistency
    row_diff = initial_shape[0] - df.shape[0]
    audit_results.append(f"Row count change: {row_diff} (from {initial_shape[0]} to {df.shape[0]})")
    
    # Detect multicollinearity (corr > 0.95)
    numeric_df = df[numeric_cols]
    corr_matrix = numeric_df.corr().abs()
    high_corr_pairs = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            if corr_matrix.iloc[i, j] > 0.95:
                high_corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j], corr_matrix.iloc[i, j]))
    
    audit_results.append(f"High correlation pairs (>0.95): {len(high_corr_pairs)}")
    if high_corr_pairs:
        audit_results.append(f"Pairs: {high_corr_pairs[:5]}")  # Show first 5
    
    # Verify BMI correlation with Height/Weight < 0.95
    if 'computed_metrics.BMI' in df.columns:
        if 'computed_metrics.Height_cm' in df.columns:
            bmi_height_corr = abs(df['computed_metrics.BMI'].corr(df['computed_metrics.Height_cm']))
            audit_results.append(f"BMI-Height correlation: {bmi_height_corr:.4f}")
        if 'computed_metrics.Weight_kg' in df.columns:
            bmi_weight_corr = abs(df['computed_metrics.BMI'].corr(df['computed_metrics.Weight_kg']))
            audit_results.append(f"BMI-Weight correlation: {bmi_weight_corr:.4f}")
    
    # Check gender balance
    if 'Gender_encoded' in df.columns:
        gender_balance = df['Gender_encoded'].value_counts().to_dict()
        audit_results.append(f"Gender balance: {gender_balance}")
    
    # Check class distribution
    if 'class_name' in df.columns:
        class_dist = df['class_name'].value_counts().to_dict()
        audit_results.append(f"Class distribution: {len(class_dist)} unique classes")
    
    # Check sport label balance
    if 'sport_label' in df.columns:
        sport_balance = df['sport_label'].value_counts().to_dict()
        audit_results.append(f"Sport labels: {len(sport_balance)} unique sports")
        audit_results.append(f"Top 5 sports: {dict(list(sport_balance.items())[:5])}")
    
    # Validate scaling
    zscore_cols = ['computed_metrics.Height_cm', 'computed_metrics.Weight_kg', 
                    'computed_metrics.BMI', 'computed_metrics.Age']
    zscore_validation = []
    for col in zscore_cols:
        if col in df.columns:
            mean_val = df[col].mean()
            std_val = df[col].std()
            zscore_validation.append(f"{col}: mean={mean_val:.4f}, std={std_val:.4f}")
    
    minmax_cols = [f'responses.{i}' for i in range(1, 8)]
    minmax_validation = []
    for col in minmax_cols:
        if col in df.columns:
            min_val = df[col].min()
            max_val = df[col].max()
            minmax_validation.append(f"{col}: min={min_val:.4f}, max={max_val:.4f}")
    
    audit_results.append(f"Z-score validation: {zscore_validation}")
    audit_results.append(f"Min-Max validation: {minmax_validation}")
    
    log_phase(8, "Quality and Leakage Audit", audit_results)
    
    return df, audit_results

# ============================================================================
# PHASE 9: Finalization
# ============================================================================

def phase9_finalization(df, label_counts, audit_results):
    """Phase 9: Finalize dataset and generate report"""
    print("\n" + "="*80)
    print("PHASE 9: Finalization")
    print("="*80)
    
    df = df.copy()
    
    # Set column order: student_id → demographics → physical → performance → engineered → responses → label
    col_order = []
    
    # Identifiers
    if 'student_id' in df.columns:
        col_order.append('student_id')
    
    # Demographics
    demo_cols = ['Gender_encoded', 'class_name'] + [c for c in df.columns if c.startswith('school_')]
    col_order.extend([c for c in demo_cols if c in df.columns])
    
    # Physical
    physical_cols = ['computed_metrics.Height_cm', 'computed_metrics.Weight_kg', 
                     'computed_metrics.BMI', 'computed_metrics.Age']
    col_order.extend([c for c in physical_cols if c in df.columns])
    
    # Performance
    perf_cols = ['computed_metrics.CoreStrengthScore', 'computed_metrics.UpperBodyStrengthScore',
                 'computed_metrics.FlexibilityScore', 'computed_metrics.EnduranceScore',
                 'computed_metrics.SpeedScore', 'computed_metrics.StrengthScore',
                 'computed_metrics.AgilityScore', 'computed_metrics.OverallScore']
    col_order.extend([c for c in perf_cols if c in df.columns])
    
    # Engineered
    engineered_cols = ['height_weight_ratio', 'strength_to_weight_ratio', 'endurance_per_bmi',
                       'flexibility_strength_ratio', 'speed_agility_ratio', 'power_index',
                       'endurance_index', 'balance_index', 'overall_fitness_index']
    col_order.extend([c for c in engineered_cols if c in df.columns])
    
    # Responses
    response_cols = [f'responses.{i}' for i in range(1, 8)]
    col_order.extend([c for c in response_cols if c in df.columns])
    
    # Label
    if 'sport_label' in df.columns:
        col_order.append('sport_label')
    if 'sport_label_encoded' in df.columns:
        col_order.append('sport_label_encoded')
    
    # Add any remaining columns
    remaining_cols = [c for c in df.columns if c not in col_order]
    col_order.extend(remaining_cols)
    
    # Reorder columns
    df = df[col_order]
    
    # Round all floats to 5 decimals
    float_cols = df.select_dtypes(include=['float32', 'float64']).columns
    for col in float_cols:
        if col != 'sport_label' and 'sport_label' not in col:  # Don't round label columns
            df[col] = df[col].round(5)
    
    # Create outputs directory if it doesn't exist
    os.makedirs('outputs', exist_ok=True)
    
    # Save final dataset
    output_path = 'data/final_model_dataset_v3.csv'
    df.to_csv(output_path, index=False)
    
    details = [
        f"Columns reordered: {len(col_order)} columns",
        f"Floats rounded to 5 decimals: {len(float_cols)} columns",
        f"Dataset saved to: {output_path}",
        f"Final shape: {df.shape[0]} rows × {df.shape[1]} columns"
    ]
    
    log_phase(9, "Finalization", details)
    
    # Generate report
    generate_report(df, label_counts, audit_results)
    
    return df

# ============================================================================
# Report Generation
# ============================================================================

def generate_report(df, label_counts, audit_results):
    """Generate final Markdown report"""
    print("\n" + "="*80)
    print("Generating Final Report")
    print("="*80)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = []
    report.append("# Final Model Dataset Rebuild Report\n")
    report.append(f"Generated: {timestamp}\n")
    report.append("\n## Overview\n")
    report.append(f"- Source file: data/Sports_Data.csv\n")
    report.append(f"- Final shape: {df.shape[0]} rows × {df.shape[1]} columns\n")
    report.append(f"- Label column: sport_label\n")
    report.append(f"- Features: {df.shape[1] - 2}\n")  # Exclude student_id and sport_label
    
    report.append("\n---\n")
    report.append("\n## Phase Summaries\n")
    
    # Add all phase logs
    report.extend(report_log)
    
    report.append("\n---\n")
    report.append("\n## Final Dataset Snapshot\n")
    report.append(f"- Shape: {df.shape[0]} rows × {df.shape[1]} columns\n")
    
    # Dtype summary
    dtypes_summary = df.dtypes.value_counts().to_dict()
    report.append(f"- Data types: {dtypes_summary}\n")
    
    # Label distribution
    if label_counts:
        report.append(f"- Unique sport labels: {len(label_counts)}\n")
        report.append(f"- Label distribution (top 10):\n")
        for sport, count in list(label_counts.items())[:10]:
            pct = (count / df.shape[0]) * 100
            report.append(f"  - {sport}: {count} ({pct:.1f}%)\n")
    
    # Validation summary
    report.append(f"- Missing values: {df.select_dtypes(include=[np.number]).isnull().sum().sum()}\n")
    report.append(f"- Infinite values: {np.isinf(df.select_dtypes(include=[np.number])).sum().sum()}\n")
    
    # Feature engineering summary
    engineered_features = ['height_weight_ratio', 'strength_to_weight_ratio', 'endurance_per_bmi',
                           'flexibility_strength_ratio', 'speed_agility_ratio', 'power_index',
                           'endurance_index', 'balance_index', 'overall_fitness_index']
    features_present = [f for f in engineered_features if f in df.columns]
    report.append(f"- Engineered features: {len(features_present)}/{len(engineered_features)}\n")
    
    report.append("\n---\n")
    report.append("\n**End of Report**\n")
    
    # Write report
    report_path = 'outputs/final_dataset_rebuild_report.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.writelines(report)
    
    print(f"[OK] Report saved to: {report_path}")


