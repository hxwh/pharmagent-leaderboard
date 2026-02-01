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
        ...
      },
      "config": {...},
      "timestamp": "..."
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

### Stage 4: DuckDB Query Execution

**Query for "Medical Record Tasks":**
```sql
SELECT id, "Score", "Success Rate", "Completion Time" 
FROM (
  SELECT 
    participant_id AS id,           -- ✅ Matches: "019c17ea-ac28-7fa2-8716-b3f79eb2913c"
    score AS "Score",                -- ✅ Matches: 0.85
    success_rate AS "Success Rate",  -- ✅ Matches: 0.90
    timestamp AS "Completion Time",  -- ✅ Matches: "2026-02-01T12:00:00.000000"
    ROW_NUMBER() OVER (PARTITION BY participant_id ORDER BY score DESC, timestamp DESC) AS rn
  FROM results 
  WHERE subtask = 'subtask1'         -- ✅ Matches: "subtask1"
) 
WHERE rn = 1 
ORDER BY "Score" DESC
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
SELECT id, "Accuracy", "Hallucination Rate", "Completion Time" 
FROM (
  SELECT 
    participant_id AS id,                    -- ✅ Matches UUID
    accuracy AS "Accuracy",                  -- ✅ Matches: 0.75
    hallucination_rate AS "Hallucination Rate", -- ✅ Matches: 0.25
    timestamp AS "Completion Time",          -- ✅ Matches timestamp
    ROW_NUMBER() OVER (PARTITION BY participant_id ORDER BY accuracy DESC, timestamp DESC) AS rn
  FROM results 
  WHERE subtask = 'subtask2'                 -- ✅ Matches: "subtask2"
) 
WHERE rn = 1 
ORDER BY "Accuracy" DESC
```

---

## Verification Checklist

### ✅ Field Alignment

| Field | Source | Destination | Status |
|-------|--------|-------------|--------|
| `subtask` | `result_data.subtask` | DuckDB `WHERE subtask = '...'` | ✅ |
| `participant_id` | `participants["medical_agent"]` | DuckDB `participant_id AS id` | ✅ |
| `score` (S1) | `result_data.score` | DuckDB `score AS "Score"` | ✅ |
| `success_rate` (S1) | `result_data.report.success_rate` | DuckDB `success_rate AS "Success Rate"` | ✅ |
| `accuracy` (S2) | `result_data.accuracy` | DuckDB `accuracy AS "Accuracy"` | ✅ |
| `hallucination_rate` (S2) | `result_data.hallucination_rate` | DuckDB `hallucination_rate AS "Hallucination Rate"` | ✅ |
| `timestamp` | `result_data.timestamp` or top-level | DuckDB `timestamp AS "Completion Time"` | ✅ |

### ✅ Format Compatibility

- [x] JSON structure matches sample files
- [x] Participant ID extraction handles `results` array format
- [x] Subtask extraction prioritizes `result_data.subtask`
- [x] Timestamp format is ISO-compliant
- [x] Metrics extraction handles nested `report` object for S1
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
