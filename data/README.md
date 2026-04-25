# Data Directory

## What's Included

| File | Rows | Description | Status |
|------|------|-------------|--------|
| `sample_students.csv` | 100 | Fully anonymized synthetic sample | ✅ **Public** |

## What's NOT Included (and Why)

| File | Reason Excluded |
|------|----------------|
| `students.csv` | Contains real student PII (names, school codes) — institutional data governance |
| `Sports_Data.csv` | Same — real assessment records from 11 schools |
| `final_model_dataset_v*.csv` | Processed versions of real student data |
| `ranking_longform.csv` | Long-form expansion of real student records |

## Sample Dataset Schema

The `sample_students.csv` file uses anonymized IDs (`ANON_001` … `ANON_100`) and contains
no real names, school codes, or identifiable information. It is suitable for:

- Development and testing
- Running the Flask web app locally
- Verifying the pipeline logic
- Demonstrating the recommendation output

### Columns

```
student_id              Anonymized ID (ANON_XXX)
Age                     Integer, years (6–18)
Gender                  M / F
classname               Class 1 – Class 12
CoreStrengthScore       Float, 1–10 (trunk stability assessment)
UpperBodyStrengthScore  Float, 1–10 (push-up / grip test)
FlexibilityScore        Float, 1–10 (sit-and-reach / ROM test)
EnduranceScore          Float, 1–10 (beep test / 12-min run proxy)
SpeedScore              Float, 1–10 (20m sprint, time-converted)
AgilityScore            Float, 1–10 (T-test / shuttle run)
OverallScore            Float, 1–10 (composite)
Height_cm               Float, centimeters
Weight_kg               Float, kilograms
BMI                     Float, kg/m²
```

## To Use the Full Pipeline

You must supply your own `students.csv` in this directory that matches the schema above.
The system will automatically detect it over `sample_students.csv` at startup.

> ⚠️ Never commit real student data to this repository.
> Verify your `.gitignore` blocks `students.csv` before any `git add`.
