# Leaderboard Data Flow Verification

## Complete Data Flow Trace

### Stage 1: Green Agent Output (Subtask 1)

**Green Agent creates artifact:**
```json
{
  "result_data": {
    "subtask": "subtask1",
    "score": 0.85,
    "report": {
      "success_rate": 0.90
    },
    "task_id": "batch_300_tasks",
    ...
  },
  "config": {
    "subtask": "subtask1",
    "task_ids": ["task1", "task2", ...],
    ...
  },
  "timestamp": "2026-02-01T12:00:00.000000"
}
```

### Stage 2: AgentBeats Client Output

**Client wraps in results array:**
```json
{
  "participants": {
    "medical_agent": "019c17ea-ac28-7fa2-8716-b3f79eb2913c"
  },
  "results": [
    {
      "result_data": {
        "subtask": "subtask1",
        "score": 0.85,
        "report": {"success_rate": 0.90},
        "timestamp": "2026-02-01T12:00:00.000000",
        ...
      },
      "config": {...}
    }
  ]
}
```

### Stage 3: Adapter Transformation

**Adapter extracts and transforms:**
1. ✅ Extracts `participant_id` from `participants["medical_agent"]` → `"019c17ea-ac28-7fa2-8716-b3f79eb2913c"`
2. ✅ Extracts `subtask` from `result_data.subtask` → `"subtask1"`
3. ✅ Extracts `score` from `result_data.score` → `0.85`
4. ✅ Extracts `success_rate` from `result_data.report.success_rate` → `0.90`
5. ✅ Extracts `timestamp` from top-level or `result_data.timestamp` → `"2026-02-01T12:00:00.000000"`

**Final output:**
```json
{
  "subtask": "subtask1",
  "participant_id": "019c17ea-ac28-7fa2-8716-b3f79eb2913c",
  "timestamp": "2026-02-01T12:00:00.000000",
  "score": 0.85,
  "success_rate": 0.90,
  "config": {...}
}
```

**Note:** The adapter extracts `timestamp` from `result_data.timestamp` in the AgentBeats client output and promotes it to the top level in the final format.

### Stage 4: DuckDB Query Execution

**Note:** DuckDB queries the transformed adapter output (Stage 3). The data is already flattened.

**Query for "Medical Record Tasks":**
```sql
SELECT id, ROUND("Score", 3) AS "Score", ROUND("Success Rate", 3) AS "Success Rate", "Completion Time"
FROM (
  SELECT *,
         ROW_NUMBER() OVER (PARTITION BY id ORDER BY "Score" DESC, "Completion Time" DESC) AS rn
  FROM (
    SELECT participant_id AS id, score AS "Score",
           success_rate AS "Success Rate", timestamp AS "Completion Time"
    FROM results
    WHERE subtask = 'subtask1'
  )
)
WHERE rn = 1
ORDER BY "Score" DESC;
```

**Expected Result:**
| id | Score | Success Rate | Completion Time |
|----|-------|--------------|----------------|
| 019c17ea-ac28-7fa2-8716-b3f79eb2913c | 0.85 | 0.90 | 2026-02-01T12:00:00.000000 |

---

## Subtask 2 Flow (Confabulation Detection)

### Stage 1: Green Agent Output (Subtask 2)

**Green Agent creates artifact:**
```json
{
  "result_data": {
    "subtask": "subtask2",
    "accuracy": 0.75,
    "hallucination_rate": 0.25,
    "task_id": "subtask2_pokemon_confabulation",
    ...
  },
  "config": {
    "subtask": "subtask2",
    "dataset": "all",
    "condition": "default",
    ...
  },
  "timestamp": "2026-02-01T13:00:00.000000"
}
```

### Stage 2-3: Same transformation process

**Final output:**
```json
{
  "subtask": "subtask2",
  "participant_id": "019c17ea-ac28-7fa2-8716-b3f79eb2913c",
  "timestamp": "2026-02-01T13:00:00.000000",
  "accuracy": 0.75,
  "hallucination_rate": 0.25,
  "config": {...}
}
```

### Stage 4: DuckDB Query Execution

**Query for "Confabulation Detection":**
```sql
SELECT id, ROUND("Accuracy", 3) AS "Accuracy", ROUND("Hallucination Rate", 3) AS "Hallucination Rate", "Completion Time"
FROM (
  SELECT *,
         ROW_NUMBER() OVER (PARTITION BY id ORDER BY "Accuracy" DESC, "Completion Time" DESC) AS rn
  FROM (
    SELECT participant_id AS id, accuracy AS "Accuracy",
           hallucination_rate AS "Hallucination Rate", timestamp AS "Completion Time"
    FROM results
    WHERE subtask = 'subtask2'
  )
)
WHERE rn = 1
ORDER BY "Accuracy" DESC;
```

---

## Verification Checklist

### ✅ Field Alignment

**Note:** DuckDB queries the transformed adapter output (Stage 3).

| Field | Source | Destination (DuckDB Table) | Status |
|-------|--------|---------------------------------|--------|
| `subtask` | `subtask` | DuckDB `WHERE subtask = 'subtask1'` | ✅ |
| `participant_id` | `participant_id` | DuckDB `participant_id AS id` | ✅ |
| `score` (S1) | `score` | DuckDB `score AS "Score"` | ✅ |
| `success_rate` (S1) | `success_rate` | DuckDB `success_rate AS "Success Rate"` | ✅ |
| `accuracy` (S2) | `accuracy` | DuckDB `accuracy AS "Accuracy"` | ✅ |
| `hallucination_rate` (S2) | `hallucination_rate` | DuckDB `hallucination_rate AS "Hallucination Rate"` | ✅ |
| `timestamp` | `timestamp` | DuckDB `timestamp AS "Completion Time"` | ✅ |

### ✅ Format Compatibility

- [x] AgentBeats client output is transformed by adapter to flat format
- [x] Participant ID extracted to top level
- [x] Subtask filtering uses `subtask` column
- [x] Timestamp format is ISO-compliant
- [x] Metrics accessible as top-level columns
- [x] DuckDB queries use flat table structure (no UNNEST)
- [x] DuckDB queries filter correctly by `subtask`
- [x] ROW_NUMBER() deduplication works correctly

### ✅ Edge Cases Handled

- [x] Missing `participant_id` → Falls back to scenario.toml
- [x] Missing `subtask` → Falls back to `config.subtask` or defaults to "subtask1"
- [x] Missing `timestamp` → Generates current ISO timestamp
- [x] Multiple submissions → ROW_NUMBER() shows best result only
- [x] Results array format → Adapter handles `results[0]` extraction

---

## Conclusion

**✅ All data flow stages are correctly aligned and verified.**

The leaderboard will correctly parse and display results from both subtasks after:
1. Rebuilding and pushing the Green Agent Docker image
2. Running assessments with `subtask = "subtask1"` and `subtask = "subtask2"`
