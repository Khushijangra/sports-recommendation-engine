"""
Percentile-Based Sports Recommender (v3 - Balanced Fix)
========================================================
Uses percentile scoring to compare students RELATIVE to their peers.

Key insight:
- A student with Speed=4 when 65% of students have Speed<5 is actually ABOVE AVERAGE
- Using percentiles normalizes scores to the population distribution
- This prevents single sports dominating due to population score skew

FIXES APPLIED (v3):
1. Minimum score floor (4.0) for very weak students
2. Hybrid scoring: stepped + gradient for better monotonicity
3. Targeted boosts for under-represented sports
4. Improved confidence calibration
"""

import numpy as np
import pandas as pd
import os
import sys
from collections import Counter
from scipy import stats

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from sport_profiles import SPORT_PROFILES, SPORTS_LIST, SCORE_ATTRIBUTES


class PercentileRecommender:
    """
    Recommender that uses population percentiles for scoring.
    
    Steps:
    1. Convert student raw scores to percentiles (0-100) relative to population
    2. Match percentile profiles to sport requirements
    3. Reward students who are in TOP percentiles for sport's key attributes
    """
    
    def __init__(self, population_df=None):
        self.sports = SPORTS_LIST
        self.attributes = SCORE_ATTRIBUTES
        
        # Calculate population percentile thresholds
        if population_df is not None:
            self.percentile_lookup = self._build_percentile_lookup(population_df)
        else:
            # Default median values if no population given
            self.percentile_lookup = {attr: {'median': 5.0, 'std': 2.0} for attr in self.attributes}
    
    def _build_percentile_lookup(self, df):
        """Build lookup tables for converting raw scores to percentiles."""
        lookup = {}
        for attr in self.attributes:
            values = df[attr].dropna().values
            lookup[attr] = {
                'values': np.sort(values),
                'median': np.median(values),
                'p25': np.percentile(values, 25),
                'p75': np.percentile(values, 75),
                'mean': np.mean(values),
                'std': np.std(values)
            }
        
        # Add height for percentile calculation
        if 'Heightcm' in df.columns:
            values = df['Heightcm'].dropna().values
            lookup['Heightcm'] = {'values': np.sort(values)}
        
        return lookup
    
    def _raw_to_percentile(self, attr, raw_value):
        """Convert raw score to percentile (0-100)."""
        lookup = self.percentile_lookup.get(attr)
        if lookup is None:
            return 50
        
        if 'values' in lookup:
            # Use actual population distribution
            pct = stats.percentileofscore(lookup['values'], raw_value, kind='rank')
        else:
            # Approximate using normal distribution
            z = (raw_value - lookup['median']) / max(lookup['std'], 0.1)
            pct = stats.norm.cdf(z) * 100
        
        return min(100, max(0, pct))
    
    def recommend(self, student_scores, height_percentile=None, bmi=None):
        """Generate recommendations based on percentile matching."""
        
        # Convert raw scores to percentiles
        student_percentiles = {}
        for attr in self.attributes:
            raw = student_scores.get(attr, 5.0)
            student_percentiles[attr] = self._raw_to_percentile(attr, raw)
        
        results = []
        
        for sport in self.sports:
            profile = SPORT_PROFILES[sport]
            
            # Calculate match score with HYBRID approach
            # Stepped thresholds + small gradient bonus for monotonicity
            score = 0
            strong_matches = 0
            total_weight = 0
            weighted_pct_sum = 0
            
            for attr in self.attributes:
                weight = profile.get(attr, 0.5)
                student_pct = student_percentiles[attr]
                
                # Stepped scoring with gradient bonus for monotonicity
                if weight >= 0.8:  # Critical attribute
                    if student_pct >= 70:
                        base_contrib = 1.0
                        strong_matches += 1
                    elif student_pct >= 50:
                        base_contrib = 0.7
                    elif student_pct >= 30:
                        base_contrib = 0.4
                    else:
                        base_contrib = 0.2
                    # Small gradient within each tier (0.1 bonus max)
                    gradient_bonus = (student_pct / 100) * 0.1
                    contribution = weight * (base_contrib + gradient_bonus)
                        
                elif weight >= 0.6:  # Important attribute
                    if student_pct >= 60:
                        base_contrib = 0.9
                        strong_matches += 1
                    elif student_pct >= 40:
                        base_contrib = 0.6
                    else:
                        base_contrib = 0.3
                    gradient_bonus = (student_pct / 100) * 0.08
                    contribution = weight * (base_contrib + gradient_bonus)
                        
                else:  # Less important - pure gradient
                    contribution = weight * (student_pct / 100) * 0.8
                
                score += contribution
                total_weight += weight
                weighted_pct_sum += student_pct * weight
            
            # Normalize to 0-10
            base_score = (score / total_weight) * 10
            
            # Height adjustment with gradient
            height_adj = 1.0
            height_pref = profile.get('height_preference')
            if height_pref and height_percentile:
                if height_pref == 'tall' and height_percentile >= 50:
                    height_adj = 1.0 + (height_percentile - 50) / 50 * 0.12
                elif height_pref == 'short' and height_percentile <= 50:
                    height_adj = 1.0 + (50 - height_percentile) / 50 * 0.12
            
            # BMI adjustment
            bmi_adj = 1.0
            bmi_pref = profile.get('bmi_preference')
            if bmi_pref and bmi:
                if bmi_pref == 'low' and bmi < 22:
                    bmi_adj = 1.0 + (22 - bmi) / 12 * 0.08
                elif bmi_pref == 'high' and bmi > 22:
                    bmi_adj = 1.0 + (bmi - 22) / 12 * 0.08
                bmi_adj = min(1.1, max(1.0, bmi_adj))
            
            # Targeted boosts for specific under-represented sports
            sport_boost = 1.0
            if sport == 'Football':
                speed_pct = student_percentiles.get('SpeedScore', 50)
                end_pct = student_percentiles.get('EnduranceScore', 50)
                if speed_pct >= 60 and end_pct >= 60:
                    sport_boost = 1.08
            elif sport == 'Basketball':
                if height_percentile and height_percentile >= 65:
                    sport_boost = 1.10
            elif sport == 'Table Tennis':
                agil_pct = student_percentiles.get('AgilityScore', 50)
                if agil_pct >= 65:
                    sport_boost = 1.08
            
            final_score = base_score * height_adj * bmi_adj * sport_boost
            
            # MINIMUM SCORE FLOOR: Very weak students get at least 4.0
            min_floor = 4.0
            final_score = max(min_floor, min(10, final_score))
            
            # IMPROVED CONFIDENCE CALIBRATION
            key_reqs = sum(1 for a in self.attributes if profile.get(a, 0) >= 0.7)
            avg_weighted_pct = weighted_pct_sum / total_weight if total_weight > 0 else 50
            
            match_ratio = strong_matches / max(key_reqs, 1) if key_reqs > 0 else 0.5
            pct_factor = avg_weighted_pct / 100
            confidence = 0.6 * match_ratio + 0.4 * pct_factor
            confidence = min(1.0, max(0.1, confidence))
            
            results.append({
                'sport': sport,
                'score': round(final_score, 2),
                'strong_matches': strong_matches,
                'confidence': round(confidence, 2),
                'height_adj': round((height_adj - 1) * 100, 1),
                'bmi_adj': round((bmi_adj - 1) * 100, 1),
                'sport_type': profile.get('sport_type', ''),
                'description': profile.get('description', ''),
                'evidence': profile.get('evidence', [])[:2]
            })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        
        for i, r in enumerate(results):
            r['rank'] = i + 1
        
        return results
    
    def recommend_for_student(self, student_row, top_n=10):
        """Full recommendation with all student details."""
        scores = {attr: student_row.get(attr, 5) for attr in self.attributes}
        
        # Height percentile calculation
        height_pct = None
        if 'Heightcm' in student_row and student_row.get('Heightcm'):
            height_pct = self._raw_to_percentile('Heightcm', student_row['Heightcm']) if 'Heightcm' in self.percentile_lookup else 50
        
        bmi = student_row.get('BMI')
        
        all_recs = self.recommend(scores, height_pct, bmi)
        
        return {
            'student_id': student_row.get('studentid', 'Unknown'),
            'student_name': student_row.get('studentname', 'Unknown'),
            'age': int(student_row.get('Age', 12)),
            'gender': student_row.get('Gender', 'Unknown'),
            'class': student_row.get('classname', ''),
            'percentiles': {attr.replace('Score', ''): round(self._raw_to_percentile(attr, scores[attr]), 1) 
                           for attr in self.attributes},
            'recommendations': all_recs[:top_n],
            'all_sports': all_recs
        }


def load_population():
    """Load student population for percentile calculation."""
    data_path = os.path.join(BASE_DIR, '..', 'data', 'students.csv')
    df = pd.read_csv(data_path)
    df.columns = [col.replace('computed_metrics.', '').replace('_', '') for col in df.columns]
    return df


def test_percentile_recommender():
    """Test the percentile-based recommender."""
    
    print("=" * 60)
    print("PERCENTILE-BASED RECOMMENDER TEST (v3)")
    print("=" * 60)
    
    # Load population for percentile calculation
    df = load_population()
    rec = PercentileRecommender(df)
    
    print(f"\nPopulation loaded: {len(df)} students")
    
    # Distribution test
    print("\n" + "-" * 60)
    tops = []
    for _, row in df.head(2000).iterrows():
        scores = {a: row[a] for a in SCORE_ATTRIBUTES}
        recs = rec.recommend(scores)
        tops.append(recs[0]['sport'])
    
    counts = Counter(tops)
    
    print("\nDistribution of Top Recommendations (n=2000):")
    for sport, count in counts.most_common():
        pct = count / 20
        print(f"  {sport:18} {count:4} ({pct:5.1f}%)")
    
    print(f"\nUnique sports recommended: {len(set(tops))}/20")
    
    # Concentration metric
    top3_concentration = sum(c for _, c in counts.most_common(3)) / 2000 * 100
    print(f"Top 3 concentration: {top3_concentration:.1f}%")
    
    # Edge case test
    print("\n" + "-" * 60)
    print("Edge Case: All 1s (very weak student)")
    weak_profile = {a: 1 for a in SCORE_ATTRIBUTES}
    recs = rec.recommend(weak_profile)
    print(f"  Top 3: {[(r['sport'], r['score']) for r in recs[:3]]}")
    print(f"  Score >= 4.0: {recs[0]['score'] >= 4.0}")
    
    # Monotonicity test
    print("\n" + "-" * 60)
    print("Monotonicity Test: CoreStrength 3->9 on Wrestling")
    low = {a: 5 for a in SCORE_ATTRIBUTES}
    low['CoreStrengthScore'] = 3
    high = {a: 5 for a in SCORE_ATTRIBUTES}
    high['CoreStrengthScore'] = 9
    
    low_recs = rec.recommend(low)
    high_recs = rec.recommend(high)
    
    low_rank = next(r['rank'] for r in low_recs if r['sport'] == 'Wrestling')
    high_rank = next(r['rank'] for r in high_recs if r['sport'] == 'Wrestling')
    
    print(f"  Low CoreStrength (3): Wrestling rank = {low_rank}")
    print(f"  High CoreStrength (9): Wrestling rank = {high_rank}")
    print(f"  Improved: {high_rank < low_rank}")
    
    return rec, counts


if __name__ == "__main__":
    rec, counts = test_percentile_recommender()
