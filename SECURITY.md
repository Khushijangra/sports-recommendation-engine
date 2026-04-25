# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest (`main`) | ✅ |

## Student Data Security

This project processes student fitness data. The full dataset is **not included** in this repository.

**What IS in this repository:**
- ✅ Source code (no embedded data)
- ✅ 100-row anonymized sample (`data/sample_students.csv`)
- ✅ Aggregate evaluation metrics (JSON files)
- ✅ Model card documentation (`models/README.md`)

**What is NOT in this repository:**
- ❌ Full student assessment dataset (institutional data governance)
- ❌ Trained model binaries (may encode training patterns)
- ❌ Intermediate pickle files containing student records

## Reporting Sensitive Data Exposure

If real student data has been accidentally committed to this repository, **do not** create a public issue. Contact the maintainer directly and describe what was found without reproducing the data. The commit will be scrubbed using `git filter-repo`.

## Vulnerability Reporting

For security vulnerabilities in the code (e.g., path traversal, injection):

1. **Do not** open a public GitHub issue
2. Email the maintainer: subject `[SECURITY] SportMatch`
3. Include: description, reproduction steps, potential impact
4. Expected response: 48 hours

## API Deployment Security

The Flask app (`app/app.py`) is designed for **local or internal network use**.

For public-facing deployment:
- Set `debug=False` in `app.run()` (already configured)
- Run behind a reverse proxy (nginx / caddy)
- Add rate limiting to `/api/recommend`
- Add authentication middleware
- Never serve with the full dataset accessible from a public endpoint

## Dependency Audit

```bash
pip install safety
safety check -r requirements.txt
```
