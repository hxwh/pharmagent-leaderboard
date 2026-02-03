# Leaderboard Submissions

This directory contains leaderboard submissions generated from assessment runs.

## Submission Structure

Each submission consists of:
- Assessment results JSON file (in `../results/` directory)
- Provenance metadata JSON file (in this directory)
- Associated pull request for review and merging

## File Naming Convention

- Results: `assessment_{timestamp}.json` (stored in `../results/`)
- Provenance: `provenance_{assessment_id}.json` (stored here)

## Submission Process

1. **Automated**: GitHub Actions workflow runs assessment and creates submission PR
2. **Manual**: Use `submission.py` script to generate and save results
3. **Review**: PR reviewers verify results before merging
4. **Merge**: Merged submissions appear on the live leaderboard

## Manual Submission

```bash
# Generate and save assessment results
python ../submission.py evaluation_output.json participant_123 --save ../results/manual_assessment.json

# Record provenance
python ../record_provenance.py manual_001 ../scenario.toml ../results/manual_assessment.json submissions/provenance_manual_001.json
```

## Quality Assurance

All submissions undergo review to ensure:
- Valid assessment results format
- Proper provenance tracking
- No duplicate or invalid data
- Compliance with benchmark rules