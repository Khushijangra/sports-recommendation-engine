#!/usr/bin/env python3
"""
SportMatch — Pre-publication safety checker.
Run this before every `git push` to verify no sensitive files
have been accidentally staged.

Usage:
    python scripts/check_before_push.py
"""

import os
import sys
import subprocess

# Files/patterns that must NEVER be committed
FORBIDDEN_PATTERNS = [
    # Student data (PII) — use EXACT filenames, not substrings
    "Sports_Data.csv",
    "students_backup",
    "final_model_dataset",
    "ranking_longform.csv",
    "gender_counts.csv",
    "split_students.json",
    "split_indices.json",
    # Research assets
    ".pdf",
    ".tex",
    ".bib",
    "IEEE_Research_Paper",
    "Finalizing Research Paper",
    "2new.tex",
    "3new.tex",
    # Model binaries
    "rf_ranker.pkl",
    "xgb_ranker_tuned.pkl",
    "xgb_ranker_production.pkl",
    "ordinal_baseline.pkl",
    "kmeans_model.pkl",
    "clustering_pca.pkl",
    # Intermediate data
    "data_prepared.pkl",
    "data_prepared_rank.pkl",
    # Dev artifacts
    "finalize_and_audit.py",
    "audit_and_verify.py",
    "generate_final_showcase.py",
    "improve_dataset.py",
    "compare_datasets_analysis.py",
]

# Full-path patterns that must match end of path exactly
FORBIDDEN_EXACT_NAMES = [
    "students.csv",   # Full dataset — never commit
]

SAFE_FILES = [
    "data/sample_students.csv",   # Anonymized sample — always safe
    "models/README.md",           # Model card — safe
]


def check_staged_files():
    """Check git staged files for forbidden patterns."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True
    )
    staged = result.stdout.strip().split("\n") if result.stdout.strip() else []
    
    violations = []
    for filepath in staged:
        filepath_lower = filepath.lower()
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.lower() in filepath_lower:
                # Check if it's an explicitly allowed safe file
                if not any(safe in filepath for safe in SAFE_FILES):
                    violations.append((filepath, pattern))
                    break
    
    return violations, staged


def check_working_tree_size():
    """Warn about large files (>5MB) in the repo."""
    large_files = []
    for root, dirs, files in os.walk("."):
        # Skip .git directory
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in files:
            filepath = os.path.join(root, f)
            try:
                size = os.path.getsize(filepath)
                if size > 5 * 1024 * 1024:  # 5MB
                    large_files.append((filepath, size / (1024 * 1024)))
            except OSError:
                pass
    return large_files


def main():
    print("=" * 60)
    print("SportMatch — Pre-push Safety Check")
    print("=" * 60)
    
    # Check staged files
    violations, staged = check_staged_files()
    
    print(f"\n[1] Staged files: {len(staged)}")
    for f in staged:
        print(f"    {f}")
    
    print(f"\n[2] Forbidden pattern check:")
    if violations:
        print("\n  ❌ VIOLATIONS FOUND — DO NOT PUSH:")
        for filepath, pattern in violations:
            print(f"     {filepath}  (matched pattern: '{pattern}')")
        print("\n  Run: git reset HEAD <filepath>  to unstage")
        sys.exit(1)
    else:
        print("  ✅ No forbidden files staged")
    
    # Check for large files
    print(f"\n[3] Large file check (>5MB):")
    large = check_working_tree_size()
    if large:
        print("  ⚠️  Large files detected (check if they should be gitignored):")
        for path, mb in large:
            print(f"     {path}  ({mb:.1f} MB)")
    else:
        print("  ✅ No oversized files in working tree")
    
    print("\n" + "=" * 60)
    print("✅ Pre-push check complete. Safe to push.")
    print("=" * 60)


if __name__ == "__main__":
    main()
