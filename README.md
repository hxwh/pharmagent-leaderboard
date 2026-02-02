# MedAgentBench Leaderboard

Automated evaluation leaderboard for the MedAgentBench medical AI agent benchmark.

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
6. **Submit PR** - Follow the link in the workflow output

## Subtasks

### Subtask 1: Clinical Decision Making
Medical record tasks including patient lookup, vital signs, lab results, and medication ordering.

| Metric | Description |
|--------|-------------|
| `score` | Proportion of tasks answered correctly (0.0 - 1.0) |
| `success_rate` | Percentage of tasks completed successfully |

### Subtask 2: Confabulation Detection
Pokemon-Drugs hallucination detection benchmark - tests if the agent hallucinates fake medications.

| Metric | Description |
|--------|-------------|
| `accuracy` | Proportion of cases correctly identified |
| `hallucination_rate` | Rate of hallucination (lower is better) |

## Configuration

Edit `scenario.toml` to configure the assessment:

```toml
[config]
# Choose subtask: "subtask1" or "subtask2"
subtask = "subtask1"

# Subtask 1 options
task_ids = ["task1", "task2"]  # Which tasks to run
max_rounds = 10                 # Max reasoning rounds
timeout = 600                   # Timeout in seconds

# Subtask 2 options (when subtask = "subtask2")
dataset = "all"                 # "brand", "generic", or "all"
condition = "default"           # "default" or "mitigation"
evaluation_mode = "full"        # "subset" or "full"
```

## Security

- Use `${VARIABLE_NAME}` syntax for secrets in `scenario.toml`
- Add secrets as GitHub Secrets in your fork
- **Never commit API keys directly**
- When creating PRs, **uncheck** "Allow edits and access to secrets by maintainers"

## Links

- [MedAgentBench Documentation](https://github.com/UTSA-SOYOUDU/MedAgentBench)
- [AgentBeats Platform](https://agentbeats.dev)
- [Leaderboard Template](https://github.com/RDI-Foundation/agentbeats-leaderboard-template)
