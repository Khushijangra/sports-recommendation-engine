"""
Sports Recommendation Web Application (v3 - 3-Tier Expert System)
===================================================================
Flask-based web app with expert-level 3-tier recommendations.

TIER 1: BEST MATCH NOW - Current abilities
TIER 2: GROWTH POTENTIAL - Developmental opportunities  
TIER 3: ENTRY SPORTS - Age-appropriate starting points
"""

from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
import os
import sys

# Add src directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, 'src')
DATA_DIR = os.path.join(BASE_DIR, 'data')
sys.path.insert(0, SRC_DIR)

# Import from expert_system
from expert_system.sport_profiles import SPORT_PROFILES, SPORTS_LIST, SCORE_ATTRIBUTES
from expert_system.three_tier_recommender import ThreeTierRecommender

app = Flask(__name__, template_folder='templates', static_folder='static')


# ============================================================
# Data Loading and Preprocessing
# ============================================================

def load_and_preprocess_data():
    """Load and preprocess the student dataset."""
    filepath = os.path.join(DATA_DIR, 'sample_students.csv')
    df = pd.read_csv(filepath)
    
    # Simplify column names
    df.columns = [col.replace('computed_metrics.', '').replace('_', '') for col in df.columns]
    
    # Fix Age anomalies
    class_to_age = {
        'Class 1': 6, 'Class 2': 7, 'Class 3': 8, 'Class 4': 9, 'Class 5': 10,
        'Class 6': 11, 'Class 7': 12, 'Class 8': 13, 'Class 9': 14, 'Class 10': 15,
        'Class 11': 16, 'Class 12': 17
    }
    
    for idx, row in df.iterrows():
        if row['Age'] < 5 or pd.isna(row['Age']):
            df.at[idx, 'Age'] = class_to_age.get(row['classname'], 12)
    
    # Fix extreme BMI values
    median_bmi = df[(df['BMI'] >= 10) & (df['BMI'] <= 50)]['BMI'].median()
    df.loc[(df['BMI'] < 10) | (df['BMI'] > 50), 'BMI'] = median_bmi
    
    return df


# ============================================================
# Initialize on startup
# ============================================================

print("Loading data...")
df = load_and_preprocess_data()
recommender = ThreeTierRecommender(df)
print(f"Loaded {len(df)} students")
print("3-Tier Expert Recommendation System initialized")


# ============================================================
# Routes
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/students/search')
def search_students():
    query = request.args.get('q', '').lower()
    limit = int(request.args.get('limit', 50))
    
    results = []
    for idx, row in df.iterrows():
        if query in str(row['studentname']).lower() or query in str(row['classname']).lower():
            results.append({
                'id': row['studentid'],
                'name': row['studentname'],
                'class': row['classname'],
                'school': row['schoolcode'],
                'age': int(row['Age']),
                'gender': row['Gender']
            })
            if len(results) >= limit:
                break
    
    return jsonify(results)


@app.route('/api/recommend/<student_id>')
def get_recommendations(student_id):
    student_rows = df[df['studentid'] == student_id]
    
    if len(student_rows) == 0:
        return jsonify({'error': 'Student not found'}), 404
    
    student = student_rows.iloc[0]
    
    # Get preferences from query params
    preferences = request.args.get('preferences', '')
    preferences_list = [p.strip() for p in preferences.split(',') if p.strip()]
    
    # Build scores dict
    scores = {attr: student.get(attr, 5) for attr in SCORE_ATTRIBUTES}
    age = int(student.get('Age', 12))
    
    # Height percentile
    height_pct = None
    if 'Heightcm' in student and student.get('Heightcm'):
        from scipy import stats
        height_vals = df['Heightcm'].dropna().values
        height_pct = stats.percentileofscore(height_vals, student['Heightcm'], kind='rank')
    
    # Get 3-tier recommendations with preferences
    recommendations = recommender.recommend(scores, age, height_pct, student.get('Gender'), preferences_list)
    
    result = {
        'student_id': student.get('studentid', 'Unknown'),
        'student_name': student.get('studentname', 'Unknown'),
        'age': age,
        'gender': student.get('Gender', 'Unknown'),
        'class': student.get('classname', ''),
        'recommendations': recommendations,
        'preferences_applied': preferences_list
    }
    
    # Add raw scores
    result['scores'] = {
        'CoreStrength': round(student.get('CoreStrength', 5), 1),
        'UpperBodyStrength': round(student.get('UpperBodyStrength', 5), 1),
        'Flexibility': round(student.get('Flexibility', 5), 1),
        'Endurance': round(student.get('Endurance', 5), 1),
        'Speed': round(student.get('Speed', 5), 1),
        'Agility': round(student.get('Agility', 5), 1),
        'Overall': round(student.get('Overall', 5), 1)
    }
    
    # Add physical attributes
    result['physical'] = {
        'height_cm': round(student.get('Heightcm', 0), 1),
        'weight_kg': round(student.get('Weightkg', 0), 1),
        'bmi': round(student.get('BMI', 0), 1)
    }
    
    return jsonify(result)


@app.route('/api/sports')
def get_sports():
    sports = []
    for sport in SPORTS_LIST:
        profile = SPORT_PROFILES[sport]
        sports.append({
            'name': sport,
            'description': profile.get('description', ''),
            'sport_type': profile.get('sport_type', ''),
            'evidence': profile.get('evidence', [])[:2],
            'requirements': {attr: profile.get(attr, 0.5) for attr in SCORE_ATTRIBUTES}
        })
    return jsonify(sports)


@app.route('/api/stats')
def get_stats():
    return jsonify({
        'total_students': len(df),
        'schools': int(df['schoolcode'].nunique()),
        'classes': sorted(df['classname'].unique().tolist()),
        'age_range': [int(df['Age'].min()), int(df['Age'].max())],
        'gender_distribution': df['Gender'].value_counts().to_dict(),
        'sports_count': len(SPORTS_LIST),
        'methodology': '3-Tier Expert Recommendation System'
    })


@app.route('/api/methodology')
def get_methodology():
    """Return information about the 3-tier methodology."""
    return jsonify({
        'name': '3-Tier Expert Recommendation System',
        'tiers': {
            'tier1': {
                'name': 'Best Match Now',
                'description': 'Sports that match current abilities',
                'logic': 'Percentile-based matching to sport profiles'
            },
            'tier2': {
                'name': 'Growth Potential',
                'description': 'Sports student could excel at with development',
                'logic': 'Age-based improvement potential analysis'
            },
            'tier3': {
                'name': 'Entry Sports',
                'description': 'Age-appropriate foundational sports',
                'logic': 'Safe starting points that build skills'
            }
        },
        'age_groups': {
            'early_childhood': '6-8 years - Fundamental movement focus',
            'late_childhood': '9-11 years - Multi-sport sampling',
            'early_adolescence': '12-14 years - Technique refinement',
            'adolescence': '15+ years - Specialization'
        },
        'sources': [
            'NIH/PubMed talent identification studies',
            'Long-Term Athlete Development (LTAD) framework',
            'Sports science physiological profiles'
        ]
    })


if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("3-TIER EXPERT RECOMMENDATION SYSTEM")
    print("=" * 50)
    print(f"Students loaded: {len(df)}")
    print(f"Sports available: {len(SPORTS_LIST)}")
    print("\nTiers:")
    print("  1. Best Match Now - Current abilities")
    print("  2. Growth Potential - Developmental opportunities")
    print("  3. Entry Sports - Age-appropriate starting points")
    print("\nStarting server at http://localhost:5000")
    print("=" * 50 + "\n")
    
    app.run(debug=False, port=5000)
