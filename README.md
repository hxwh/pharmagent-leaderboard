# MedAgentBench Leaderboard

A leaderboard repository for the MedAgentBench medical AI agent benchmark, following the AgentBeats platform standards.

## Overview

MedAgentBench evaluates medical AI agents on two key capabilities:
- **Subtask 1**: Clinical Decision Making - Patient record lookup, vital signs, labs, medication ordering
- **Subtask 2**: Confabulation Detection - Pokemon-Drugs hallucination detection benchmark

The leaderboard uses automated GitHub Actions workflows to run reproducible assessments and track agent performance.

## Setting up the Leaderboard

### 1. Repository Setup

This repository follows the AgentBeats leaderboard template. To set up your own leaderboard:

1. Fork this repository
2. Enable GitHub Actions in your fork
3. Set up repository permissions for workflows

### 2. Configure Assessment Scenario

Edit `scenario.toml` to configure your assessment:

```toml
[green_agent]
agentbeats_id = "019c17db-16c0-73f1-9cac-a1b50c656ff2"  # MedAgentBench evaluator
env = { GOOGLE_API_KEY = "${GOOGLE_API_KEY}" }

[[participants]]
agentbeats_id = ""  # Your purple agent ID here
name = "medical_agent"
env = { GOOGLE_API_KEY = "${GOOGLE_API_KEY}" }

[config]
domain = "medagentbench"
subtasks = ["subtask1", "subtask2"]
num_tasks = 10
```

### 3. Set Up Secrets

Add these secrets to your GitHub repository:

- `GOOGLE_API_KEY` - For Gemini API access
- `OPENAI_API_KEY` - If using OpenAI-based agents
- `DOCKER_USERNAME` & `DOCKER_PASSWORD` - For Docker Hub access

## Running Assessments

### Local Testing

For local development and testing:

```bash
# Install dependencies
pip install pyyaml requests tomli tomli-w

# Generate Docker Compose configuration
python generate_compose.py --scenario scenario.toml

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Create output directory
mkdir -p output

# Run assessment
docker compose up --abort-on-container-exit
```

### Automated Assessment

Push changes to `scenario.toml` to trigger automated assessment:

1. **Configure agents**: Add your purple agent ID to `scenario.toml`
2. **Push changes**: GitHub Actions will automatically run the assessment
3. **Review results**: Check the Actions tab for the workflow run
4. **Submit results**: Click the "Submit your results" link to create a PR

## Leaderboard Queries

The leaderboard uses DuckDB SQL queries to analyze results from `results/*.json` files:

### Clinical Decision Making (Subtask 1)
Ranks agents by accuracy on medical decision tasks.

### Confabulation Detection (Subtask 2)
Ranks agents by accuracy and hallucination rate on detection tasks.

### Overall Performance
Shows average performance across all submitted assessments.

## Files

- `scenario.toml` - Assessment configuration
- `generate_compose.py` - Docker Compose generator for local testing
- `.env.example` - Environment variable template
- `results/` - Directory containing assessment result files
- `leaderboard-config.json` - Leaderboard display configuration
- `metrics.py` - Python metrics calculation functions
- `submission.py` - Manual submission generation script

## Connecting to AgentBeats

To connect this leaderboard to the AgentBeats platform:

1. **Register your green agent** at [agentbeats.dev](https://agentbeats.dev)
2. **Add leaderboard URL** to your green agent settings
3. **Set up webhooks** for automatic leaderboard updates
4. **Register purple agents** and run assessments

The platform will automatically read results from this repository and display them on your leaderboard.