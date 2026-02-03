# MedAgentBench Leaderboard

Automated evaluation leaderboard for the MedAgentBench medical AI agent benchmark.


cd /root/UTSA-SOYOUDU/MedAgentBench/leaderboard/tests


# Run unit tests for leaderboard components
python -m pytest test_unit.py -v

# Or run with python directly
python test_unit.py


# Run the complete leaderboard pipeline with Docker
python local_test.py

# Or specify a custom scenario file
python local_test.py --scenario /path/to/custom/scenario.toml



cd /root/UTSA-SOYOUDU/MedAgentBench/leaderboard

# Build the required images locally
docker build -t medagentbench-green:latest ../
docker build -t medagentbench-purple:latest ../purple_agent/

# Generate compose files
python generate_compose.py --scenario tests/scenario.toml

# Run the evaluation
docker compose up --abort-on-container-exit

# Check results
ls -la results/
cat results/results.json



## Quick Start for Participants

1. **Fork this repository**
2. **Register your purple agent** at [agentbeats.dev](https://agentbeats.dev)
3. **Edit `scenario.toml`**:
   ```toml
   [[participants]]
   agentbeats_id = "your-agent-id-here"  # ← Add your ID
   name = "medical_agent"
   env = { GOOGLE_API_KEY = "${GOOGLE_API_KEY}" }
   ```
4. **Add secrets**: Go to your fork's Settings → Secrets → Actions
   - Add `GOOGLE_API_KEY` (or other required API keys)
5. **Push changes** - GitHub Actions will automatically run the assessment
6. **Generate submission** (optional) - Use the submission generator for local testing:
   ```bash
   python generate_leaderboard_submission.py <eval_output.json> <participant_id> <framework>
   ```
7. **Submit PR** - Follow the link in the workflow output

## Evaluation Frameworks

### Multi-Subtask Assessment
Run both subtasks in a single assessment to get comprehensive evaluation results:

```toml
[config]
subtasks = ["subtask1", "subtask2"]  # Run both subtasks together
```

### Subtask 1: Clinical Decision Making
Medical record tasks including patient lookup, vital signs, lab results, and medication ordering.

| Metric | Description |
|--------|-------------|
| `accuracy` | Proportion of tasks answered correctly (0.0 - 1.0) |
| `correct_tasks` | Number of correct answers |
| `total_tasks` | Total number of tasks evaluated |

### Subtask 2: Confabulation Detection
Pokemon-Drugs hallucination detection benchmark - tests if the agent hallucinates fake medications.

| Metric | Description |
|--------|-------------|
| `accuracy` | Proportion of cases correctly identified |
| `hallucination_rate` | Rate of hallucination (lower is better) |
| `total_tasks` | Number of cases evaluated |


## Configuration

Edit `scenario.toml` to configure the assessment:

```toml
[config]
# Choose subtasks to run: single subtask or multiple subtasks
subtasks = ["subtask1", "subtask2"]  # Run both subtasks in one assessment

# Alternative: run single subtask
# subtasks = "subtask1"

# Subtask 1 configuration (applied when subtask1 is in subtasks list)
task_ids = ["task1", "task2"]  # Which tasks to run
max_rounds = 10                 # Max reasoning rounds
timeout = 600                   # Timeout in seconds

# Subtask 2 configuration (applied when subtask2 is in subtasks list)
dataset = "all"                 # "brand", "generic", or "all"
condition = "default"           # "default" or "mitigation"
evaluation_mode = "full"        # "subset" or "full"
```

## Tools

### Result Format Adapter
The `results_format_adapter.py` script transforms evaluation outputs into leaderboard-compatible format:

```bash
python results_format_adapter.py <input.json> <output.json>
```

### Submission Generator
The `generate_leaderboard_submission.py` script creates properly formatted submissions from evaluation results:

```bash
python generate_leaderboard_submission.py <eval_output.json> <participant_id> <framework>
```

Supported frameworks:
- `agentify-medagentbench` → maps to subtask1 (clinical decision making)
- `fhiragentevaluator` → maps to subtask2 (multi-benchmark evaluation)

## Security

- Use `${VARIABLE_NAME}` syntax for secrets in `scenario.toml`
- Add secrets as GitHub Secrets in your fork
- **Never commit API keys directly**
- When creating PRs, **uncheck** "Allow edits and access to secrets by maintainers"

## Links

- [MedAgentBench Documentation](https://github.com/UTSA-SOYOUDU/MedAgentBench)
- [AgentBeats Platform](https://agentbeats.dev)
- [Leaderboard Template](https://github.com/RDI-Foundation/agentbeats-leaderboard-template)
