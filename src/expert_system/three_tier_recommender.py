"""
3-Tier Expert Recommendation System
=====================================
Provides genuine, expert-level sports recommendations using 3 tiers:

TIER 1: BEST MATCH NOW
- Current abilities match sport requirements
- What they're good at RIGHT NOW

TIER 2: GROWTH POTENTIAL  
- Sports they could excel at with development
- Based on age-appropriate improvement potential
- "You have the base, work on X to excel at Y"

TIER 3: ENTRY SPORTS
- Age-appropriate foundational sports
- Safe starting points for beginners
- Build fundamental movement skills

This approach mirrors how real sports coaches think:
- Not just "what fits now" but "what could they become"
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


# ==============================================================================
# AGE-APPROPRIATE SPORTS MAPPING
# ==============================================================================

# Sports appropriate for each age group (based on sports science guidelines)
AGE_APPROPRIATE_SPORTS = {
    # Ages 6-8: Focus on fundamental movement, play-based learning
    'early_childhood': {
        'ages': (6, 8),
        'sports': ['Swimming', 'Gymnastics', 'Athletics', 'Football', 'Badminton', 
                   'Table Tennis', 'Kho-Kho'],
        'avoid': ['Boxing', 'Wrestling', 'Weightlifting', 'Judo']  # Too physical
    },
    # Ages 9-11: Introduction to technique, multi-sport sampling
    'late_childhood': {
        'ages': (9, 11),
        'sports': ['Swimming', 'Gymnastics', 'Athletics', 'Football', 'Basketball',
                   'Volleyball', 'Badminton', 'Table Tennis', 'Hockey', 'Tennis',
                   'Cycling', 'Kho-Kho', 'Kabaddi', 'Archery', 'Fencing'],
        'avoid': ['Boxing', 'Weightlifting']  # Heavy contact/load
    },
    # Ages 12-14: Sport specialization begins, technique refinement
    'early_adolescence': {
        'ages': (12, 14),
        'sports': SPORTS_LIST,  # All sports appropriate
        'avoid': []
    },
    # Ages 15+: Full specialization possible
    'adolescence': {
        'ages': (15, 18),
        'sports': SPORTS_LIST,  # All sports appropriate
        'avoid': []
    }
}

# Entry/Foundational sports by age - safe starting points
ENTRY_SPORTS = {
    'early_childhood': ['Swimming', 'Athletics', 'Gymnastics'],
    'late_childhood': ['Swimming', 'Athletics', 'Football', 'Badminton'],
    'early_adolescence': ['Swimming', 'Athletics', 'Cycling', 'Badminton'],
    'adolescence': ['Swimming', 'Athletics', 'Cycling', 'Football']
}

# Sports that build foundation for others
SPORT_PROGRESSION = {
    'Swimming': ['Cycling', 'Athletics'],  # Endurance base
    'Athletics': ['Football', 'Hockey', 'Kabaddi', 'Kho-Kho'],  # Speed/agility base
    'Gymnastics': ['Judo', 'Wrestling', 'Fencing', 'Volleyball'],  # Core/flexibility
    'Badminton': ['Tennis', 'Table Tennis', 'Fencing'],  # Racket sports
    'Football': ['Hockey', 'Basketball', 'Kabaddi'],  # Team field sports
}

# Similar sports (to avoid recommending both in top 3)
SIMILAR_SPORTS = {
    'Archery': ['Shooting'],
    'Shooting': ['Archery'],
    'Football': ['Hockey'],
    'Hockey': ['Football'],
    'Tennis': ['Badminton', 'Table Tennis'],
    'Badminton': ['Tennis', 'Table Tennis'],
    'Table Tennis': ['Tennis', 'Badminton'],
    'Judo': ['Wrestling'],
    'Wrestling': ['Judo'],
}

# Developmental improvement potential by age (how much can scores improve)
AGE_IMPROVEMENT_POTENTIAL = {
    6: {'speed': 0.8, 'endurance': 0.7, 'strength': 0.6, 'flexibility': 0.9, 'agility': 0.8},
    7: {'speed': 0.8, 'endurance': 0.7, 'strength': 0.6, 'flexibility': 0.9, 'agility': 0.8},
    8: {'speed': 0.8, 'endurance': 0.75, 'strength': 0.65, 'flexibility': 0.85, 'agility': 0.8},
    9: {'speed': 0.75, 'endurance': 0.75, 'strength': 0.7, 'flexibility': 0.8, 'agility': 0.75},
    10: {'speed': 0.75, 'endurance': 0.8, 'strength': 0.7, 'flexibility': 0.75, 'agility': 0.75},
    11: {'speed': 0.7, 'endurance': 0.8, 'strength': 0.75, 'flexibility': 0.7, 'agility': 0.7},
    12: {'speed': 0.65, 'endurance': 0.85, 'strength': 0.8, 'flexibility': 0.65, 'agility': 0.65},
    13: {'speed': 0.6, 'endurance': 0.85, 'strength': 0.85, 'flexibility': 0.6, 'agility': 0.6},
    14: {'speed': 0.55, 'endurance': 0.8, 'strength': 0.85, 'flexibility': 0.55, 'agility': 0.55},
    15: {'speed': 0.5, 'endurance': 0.75, 'strength': 0.8, 'flexibility': 0.5, 'agility': 0.5},
    16: {'speed': 0.45, 'endurance': 0.7, 'strength': 0.75, 'flexibility': 0.45, 'agility': 0.45},
    17: {'speed': 0.4, 'endurance': 0.65, 'strength': 0.7, 'flexibility': 0.4, 'agility': 0.4},
    18: {'speed': 0.35, 'endurance': 0.6, 'strength': 0.65, 'flexibility': 0.35, 'agility': 0.35},
}


# ==============================================================================
# 3-TIER RECOMMENDER CLASS
# ==============================================================================

class ThreeTierRecommender:
    """
    Expert-level 3-tier sports recommendation system.
    
    Provides:
    - TIER 1: Best current match (top 3 sports)
    - TIER 2: Growth potential (where they could excel with development)
    - TIER 3: Entry sports (age-appropriate starting points)
    """
    
    def __init__(self, population_df=None):
        self.sports = SPORTS_LIST
        self.attributes = SCORE_ATTRIBUTES
        
        # Build percentile lookup for population-relative scoring
        if population_df is not None:
            self.percentile_lookup = self._build_percentile_lookup(population_df)
        else:
            self.percentile_lookup = {}
    
    def _build_percentile_lookup(self, df):
        """Build lookup tables for converting raw scores to percentiles."""
        lookup = {}
        for attr in self.attributes:
            values = df[attr].dropna().values
            lookup[attr] = {'values': np.sort(values)}
        
        if 'Heightcm' in df.columns:
            values = df['Heightcm'].dropna().values
            lookup['Heightcm'] = {'values': np.sort(values)}
        
        return lookup
    
    def _raw_to_percentile(self, attr, raw_value):
        """Convert raw score to percentile (0-100)."""
        lookup = self.percentile_lookup.get(attr)
        if lookup is None or 'values' not in lookup:
            return 50
        return stats.percentileofscore(lookup['values'], raw_value, kind='rank')
    
    def _get_age_group(self, age):
        """Get the age group category."""
        if age <= 8:
            return 'early_childhood'
        elif age <= 11:
            return 'late_childhood'
        elif age <= 14:
            return 'early_adolescence'
        else:
            return 'adolescence'
    
    def _get_appropriate_sports(self, age):
        """Get list of age-appropriate sports."""
        age_group = self._get_age_group(age)
        info = AGE_APPROPRIATE_SPORTS[age_group]
        return info['sports'], info['avoid']
    
    def _calculate_current_match(self, student_scores, sport):
        """Calculate how well student currently matches a sport."""
        profile = SPORT_PROFILES[sport]
        
        score = 0
        strong_matches = 0
        total_weight = 0
        
        for attr in self.attributes:
            raw = student_scores.get(attr, 5)
            pct = self._raw_to_percentile(attr, raw)
            weight = profile.get(attr, 0.5)
            
            # Contribution based on percentile and weight
            if weight >= 0.8:  # Critical
                if pct >= 70:
                    contrib = 1.0
                    strong_matches += 1
                elif pct >= 50:
                    contrib = 0.7
                elif pct >= 30:
                    contrib = 0.4
                else:
                    contrib = 0.2
            elif weight >= 0.6:  # Important
                if pct >= 60:
                    contrib = 0.9
                    strong_matches += 1
                elif pct >= 40:
                    contrib = 0.6
                else:
                    contrib = 0.3
            else:  # Minor
                contrib = 0.4 + (pct / 100) * 0.4
            
            score += weight * contrib
            total_weight += weight
        
        normalized = (score / total_weight) * 10 if total_weight > 0 else 5
        return normalized, strong_matches
    
    def _calculate_potential(self, student_scores, sport, age):
        """Calculate growth potential for a sport."""
        profile = SPORT_PROFILES[sport]
        age = min(18, max(6, age))
        improvement = AGE_IMPROVEMENT_POTENTIAL.get(age, AGE_IMPROVEMENT_POTENTIAL[12])
        
        # Map attribute to improvement category
        attr_to_category = {
            'CoreStrengthScore': 'strength',
            'UpperBodyStrengthScore': 'strength',
            'FlexibilityScore': 'flexibility',
            'EnduranceScore': 'endurance',
            'SpeedScore': 'speed',
            'AgilityScore': 'agility'
        }
        
        potential_score = 0
        improvement_areas = []
        
        for attr in self.attributes:
            raw = student_scores.get(attr, 5)
            weight = profile.get(attr, 0.5)
            category = attr_to_category.get(attr, 'strength')
            potential = improvement.get(category, 0.5)
            
            # If student is weak but can improve, this is potential
            if raw < 6 and weight >= 0.7 and potential >= 0.6:
                # High potential area
                gain = (6 - raw) * potential * weight
                potential_score += gain
                improvement_areas.append(attr.replace('Score', ''))
            elif raw >= 6 and weight >= 0.7:
                # Already good, steady contribution
                potential_score += weight * 0.5
        
        return potential_score, improvement_areas
    
    def recommend(self, student_scores, age, height_percentile=None, gender=None, preferences=None):
        """
        Generate 3-tier recommendations.
        
        Args:
            preferences: List of sports the student is interested in (optional)
        
        Returns:
        {
            'tier1_best_match': [top 3 current matches],
            'tier2_potential': [top 3 growth opportunities],  
            'tier3_entry': [age-appropriate entry sports]
        }
        """
        preferences = preferences or []
        age = int(age)
        age_group = self._get_age_group(age)
        appropriate_sports, avoid_sports = self._get_appropriate_sports(age)
        
        # =====================
        # TIER 1: BEST MATCH NOW
        # =====================
        tier1_results = []
        
        for sport in appropriate_sports:
            if sport in avoid_sports:
                continue
            
            match_score, strong_matches = self._calculate_current_match(student_scores, sport)
            profile = SPORT_PROFILES[sport]
            
            # Height/BMI adjustments
            if profile.get('height_preference') == 'tall' and height_percentile and height_percentile >= 60:
                match_score *= 1.08
            
            # Preference boost (15% if student interested)
            preferred = sport in preferences
            if preferred:
                match_score *= 1.15
            
            tier1_results.append({
                'sport': sport,
                'score': round(max(4, min(10, match_score)), 1),
                'strong_matches': strong_matches,
                'type': profile.get('sport_type', ''),
                'reason': self._generate_reason(student_scores, profile, sport),
                'preferred': preferred
            })
        
        tier1_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Apply diversity filter - avoid recommending similar sports in top 3
        tier1_results = self._apply_diversity(tier1_results)
        
        # =====================
        # TIER 2: GROWTH POTENTIAL
        # =====================
        tier2_results = []
        
        for sport in appropriate_sports:
            if sport in avoid_sports:
                continue
            
            # Only consider sports where current match is moderate (4-7)
            current_score, _ = self._calculate_current_match(student_scores, sport)
            if current_score >= 8:  # Already a top match, skip
                continue
            
            potential_score, improvement_areas = self._calculate_potential(student_scores, sport, age)
            
            if potential_score > 0.5 and improvement_areas:
                tier2_results.append({
                    'sport': sport,
                    'potential_score': round(potential_score, 2),
                    'current_score': round(current_score, 1),
                    'improve_areas': improvement_areas[:2],
                    'reason': f"Work on {', '.join(improvement_areas[:2])} to unlock potential"
                })
        
        tier2_results.sort(key=lambda x: x['potential_score'], reverse=True)
        
        # =====================
        # TIER 3: ENTRY SPORTS
        # =====================
        entry_sports = ENTRY_SPORTS.get(age_group, ['Swimming', 'Athletics'])
        
        tier3_results = []
        for sport in entry_sports:
            if sport in appropriate_sports and sport not in avoid_sports:
                match_score, _ = self._calculate_current_match(student_scores, sport)
                progressions = SPORT_PROGRESSION.get(sport, [])
                
                tier3_results.append({
                    'sport': sport,
                    'score': round(max(4, min(10, match_score)), 1),
                    'leads_to': progressions[:2] if progressions else [],
                    'reason': f"Foundational sport, builds base for {', '.join(progressions[:2]) if progressions else 'many sports'}"
                })
        
        return {
            'tier1_best_match': tier1_results[:3],
            'tier2_potential': tier2_results[:3],
            'tier3_entry': tier3_results[:3],
            'age_group': age_group,
            'sports_avoided': avoid_sports
        }
    
    def _apply_diversity(self, results):
        """Apply diversity filter to avoid recommending similar sports."""
        if len(results) <= 1:
            return results
        
        diverse_results = [results[0]]  # Always keep #1
        
        for result in results[1:]:
            sport = result['sport']
            # Check if similar sport already in diverse_results
            dominated = False
            for existing in diverse_results:
                similar = SIMILAR_SPORTS.get(sport, [])
                if existing['sport'] in similar:
                    dominated = True
                    break
            
            if not dominated:
                diverse_results.append(result)
            
            if len(diverse_results) >= 3:
                break
        
        # If we don't have 3 diverse, fill from remaining
        for result in results:
            if len(diverse_results) >= 3:
                break
            if result not in diverse_results:
                diverse_results.append(result)
        
        return diverse_results[:3]
    
    def _generate_reason(self, student_scores, profile, sport_name):
        """Generate specific, human-readable reason for recommendation."""
        strengths = []
        percentiles = []
        
        for attr in self.attributes:
            raw = student_scores.get(attr, 5)
            pct = self._raw_to_percentile(attr, raw)
            weight = profile.get(attr, 0.5)
            
            if pct >= 70 and weight >= 0.7:
                attr_name = attr.replace('Score', '').replace('UpperBody', 'Upper Body ')
                strengths.append((attr_name, int(pct)))
            percentiles.append((attr.replace('Score', ''), pct, weight))
        
        if strengths:
            # Detailed reason with percentiles
            top_strength = strengths[0]
            return f"Your {top_strength[0].lower()} (top {100-top_strength[1]}%) matches {sport_name}'s requirements"
        else:
            # Find best relative match
            percentiles.sort(key=lambda x: x[1] * x[2], reverse=True)
            best = percentiles[0]
            return f"Good balance of attributes, especially {best[0].lower()}"
    
    def recommend_for_student(self, student_row, top_n=3):
        """Generate complete recommendation for a student."""
        scores = {attr: student_row.get(attr, 5) for attr in self.attributes}
        age = int(student_row.get('Age', 12))
        gender = student_row.get('Gender', 'Unknown')
        
        # Height percentile
        height_pct = None
        if 'Heightcm' in student_row and student_row.get('Heightcm'):
            height_pct = self._raw_to_percentile('Heightcm', student_row['Heightcm'])
        
        recommendations = self.recommend(scores, age, height_pct, gender)
        
        return {
            'student_id': student_row.get('studentid', 'Unknown'),
            'student_name': student_row.get('studentname', 'Unknown'),
            'age': age,
            'gender': gender,
            'class': student_row.get('classname', ''),
            'scores': {attr.replace('Score', ''): round(student_row.get(attr, 5), 1) 
                      for attr in self.attributes},
            'recommendations': recommendations
        }


# ==============================================================================
# TEST FUNCTION
# ==============================================================================

def test_three_tier():
    """Test the 3-tier recommender."""
    from percentile_recommender import load_population
    
    print("=" * 70)
    print("3-TIER EXPERT RECOMMENDATION SYSTEM TEST")
    print("=" * 70)
    
    df = load_population()
    rec = ThreeTierRecommender(df)
    
    print(f"Population: {len(df)} students")
    
    # Test cases by age
    test_cases = [
        {
            'name': 'Young Child (Age 7)',
            'profile': {'Age': 7, 'CoreStrengthScore': 5, 'UpperBodyStrengthScore': 4,
                       'FlexibilityScore': 7, 'EnduranceScore': 6, 'SpeedScore': 5, 'AgilityScore': 6}
        },
        {
            'name': 'Pre-Teen (Age 11)',
            'profile': {'Age': 11, 'CoreStrengthScore': 6, 'UpperBodyStrengthScore': 5,
                       'FlexibilityScore': 8, 'EnduranceScore': 8, 'SpeedScore': 4, 'AgilityScore': 6}
        },
        {
            'name': 'Teenager (Age 15)',
            'profile': {'Age': 15, 'CoreStrengthScore': 8, 'UpperBodyStrengthScore': 8,
                       'FlexibilityScore': 6, 'EnduranceScore': 9, 'SpeedScore': 6, 'AgilityScore': 7}
        },
        {
            'name': 'Speed Athlete (Age 13)',
            'profile': {'Age': 13, 'CoreStrengthScore': 5, 'UpperBodyStrengthScore': 5,
                       'FlexibilityScore': 6, 'EnduranceScore': 6, 'SpeedScore': 9, 'AgilityScore': 9}
        },
    ]
    
    for case in test_cases:
        print(f"\n{'='*50}")
        print(f"TEST: {case['name']}")
        print(f"{'='*50}")
        
        scores = {k: v for k, v in case['profile'].items() if k != 'Age'}
        age = case['profile']['Age']
        
        result = rec.recommend(scores, age)
        
        print(f"\nAge Group: {result['age_group']}")
        if result['sports_avoided']:
            print(f"Sports Avoided (age-inappropriate): {result['sports_avoided']}")
        
        print(f"\nTIER 1 - BEST MATCH NOW:")
        for r in result['tier1_best_match']:
            print(f"  {r['sport']:15} Score: {r['score']}/10 - {r['reason']}")
        
        print(f"\nTIER 2 - GROWTH POTENTIAL:")
        for r in result['tier2_potential']:
            print(f"  {r['sport']:15} Potential: {r['potential_score']:.1f} - {r['reason']}")
        
        print(f"\nTIER 3 - ENTRY SPORTS:")
        for r in result['tier3_entry']:
            leads_to = ', '.join(r['leads_to']) if r['leads_to'] else 'many sports'
            print(f"  {r['sport']:15} Score: {r['score']}/10 - Leads to: {leads_to}")
    
    return rec


if __name__ == "__main__":
    rec = test_three_tier()
